"""
Bulk (sub)category changes for Yoda research groups.
"""

import argparse
import csv
import sys
from typing import List, Optional, Sequence, Set, Tuple, Type

from irods.models import Group, User, UserMeta

from yclienttools import common_args, common_config, common_queries, yoda_names
from yclienttools.common_queries import collection_exists
from yclienttools import session as s
from yclienttools.common_rules import RuleInterface


# ============================================================================
# Entry point and command-line parsing
# ============================================================================

def entry() -> None:
    """Entry point."""
    args = _get_args()
    yoda_version = args.yoda_version if args.yoda_version is not None else common_config.get_default_yoda_version()

    # -datamanagers_new_category is required, can be empty string => empty list
    args.datamanagers_new_category = _split_datamanagers(args.datamanagers_new_category)

    data = parse_csv_file_recat(args.csvfile)
    if len(data) == 0:
        _exit_with_error(None, "CSV contains no data rows")

    if args.check:
        _log(args, "CSV check (offline) OK. Rows: {}".format(len(data)))
        _log(
            args,
            "Datamanagers for NEW categories (CLI): {}".format(
                ";".join(args.datamanagers_new_category) if args.datamanagers_new_category else "(none)"
            ),
        )
        if args.verbose:
            print_parsed_data(data)
        sys.exit(0)

    session = s.setup_session(yoda_version)
    rule_interface = RuleInterface(session, yoda_version)

    exit_code = 0

    try:
        _ensure_rodsadmin(session)
        _run_online_checks(session, rule_interface, args, data)
        result = _apply_data(session, rule_interface, args, data)

        if not args.dry_run:
            problems, notes = _verify_changes(session, rule_interface, args, result)
            _report_result(args, result, problems, notes)
            # Only a failed verification is an error. A skipped row is the
            # safety check declining to move a group that still has unprocessed
            # publications: a normal outcome, reported in the summary above.
            if problems:
                exit_code = 1

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)
        exit_code = 1

    except Exception as e:
        print("Error: {}".format(e), file=sys.stderr)
        exit_code = 1

    finally:
        session.cleanup()

    sys.exit(exit_code)


def _get_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=_get_format_help_text(),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    common_args.add_default_args(parser)

    parser.add_argument("csvfile", help="CSV file containing recategorization records.")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", "-c", action="store_true", help="Check mode: verify CSV format and content.")
    mode.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Dry-run mode: connects to iRODS, validates, and prints what would change. "
        "Does not modify any groups.",
    )

    parser.add_argument(
        "--datamanagers-new-category",
        "--datamagers-new-category",
        dest="datamanagers_new_category",
        required=True,
        help=(
            "Required. List of datamanager usernames (separated by ';') to assign as managers "
            "For a new datamanager-<category> group to be created.\n"
            "Use an empty string (\"\") to explicitly allow creating new categories without datamanagers.\n"
            "Example: --datamanagers-new-category 'dm1@example.org;dm2@example.org'\n"
            "Example (no DMs): --datamanagers-new-category ''"
        ),
    )
    parser.add_argument('--create-sram-co', action='store_true', default=False,
                        help='Create SRAM CO for new groups (only available on Yoda 2.1+)')
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output.")
    return parser.parse_args()


def _get_format_help_text() -> str:
    return r"""
        The CSV file is expected to include the following labels in its header (the first row):
        'groupname'   = full research group name (must start with "research-")
        'category'    = new category (mandatory)
        'subcategory' = new subcategory (optional; empty means do not change subcategory)

        Datamanagers:
        - Use the required command line option --datamanagers-new-category.
        - It accepts a ';' separated list, or an empty string "" to allow no datamanagers.

        Notes:
        - CSV delimiter may be ','
        - Empty rows are ignored.
        - Safety check: a row is skipped if the group still has unprocessed publications,
          that is if /<zone>/home/datamanager-<old category>/vault-<group> exists. This is
          checked per group, so the other rows are still applied and a skipped group stays
          in its original category. Skipped rows are listed at the end of the run.

        Datamanager groups:
        - A datamanager group is created only when the new category does not have one yet.
          It is filed under its own category, so datamanager-<category> gets
          category = <category> and subcategory = <category>.
        - An EXISTING datamanager group is never modified. Its subcategory is left as it is
          and the datamanagers given on the command line are NOT added to it, because doing
          so would mean changing a group this script did not create. Any such group is
          listed at the end of the run, together with what was left undone, so that it can
          be corrected by hand in the portal group manager.
        - The datamanager group of the OLD category is left in place, including its category.

        After the changes have been applied, the result is read back from iRODS and reported.
        The exit status is non-zero if a change did not take effect. Skipped rows do not
        affect it: they are listed in the summary and the run itself did what it could.

        Example CSV:
        groupname,category,subcategory
        research-abc,departmentx,teama
        research-def,departmenty,

        Example usage:
        yrecatgroups input.csv --datamanagers-new-category 'dm1@example.org;dm2@example.org'
        yrecatgroups input.csv --datamanagers-new-category ''   # allow creating new categories without DMs
    """


# ============================================================================
# Output logging and error handling
# ============================================================================

def _basic(args: argparse.Namespace, message: str) -> None:
    """Progress output when NOT running with --verbose."""
    if not getattr(args, "verbose", False):
        print(message)


def _log(args: argparse.Namespace, message: str) -> None:
    """Log to stdout only if verbose enabled."""
    if getattr(args, "verbose", False):
        print(message)


def _warn(message: str) -> None:
    print("Warning: {}".format(message), file=sys.stderr)


def _exit_with_error(session, message: str) -> None:
    print("Error: {}".format(message), file=sys.stderr)
    if session is not None:
        session.cleanup()
    sys.exit(1)


# ============================================================================
# CSV parsing and validation
# ============================================================================

RecatRow = Tuple[str, str, str, int]
# (groupname, category, subcategory, row_number)


def _sniff_csv_dialect_or_exit(csv_file) -> Type[csv.Dialect]:
    """
    Sniff CSV sample dialect, to ensure ',' is used as delimiter.
    """
    try:
        sample = csv_file.read(4096)
        dialect = csv.Sniffer().sniff(sample, delimiters=",")
    except Exception:
        _exit_with_error(None, 'CSV is not correctly delimited with ","')
    finally:
        csv_file.seek(0)
    return dialect


def _normalize_header(fieldnames: Sequence[str]) -> List[str]:
    """
    Removing trailing spaces.
    """
    return [h.strip() for h in fieldnames]


def _validate_header(header: Sequence[str]) -> None:
    """Check required fields and unknown fields in CSV header."""
    required = set(_get_csv_required_labels())
    possible = set(_get_csv_possible_labels())

    missing = [h for h in required if h not in header]
    if missing:
        _exit_with_error(None, 'CSV header is missing compulsory field(s): {}'.format(", ".join(missing)))

    unknown = [h for h in header if h not in possible]
    if unknown:
        _exit_with_error(None, 'CSV header contains unknown field(s): {}'.format(", ".join(unknown)))


def _is_effectively_empty_row(row: dict) -> bool:
    """Determine if a CSV row is effectively empty (ignoring extra columns)."""
    if not row:
        return True
    for k, v in row.items():
        if k == "__extra__":
            continue
        if v is not None and str(v).strip() != "":
            return False
    return True


def _parse_and_validate_row(row: dict, row_number: int, seen_groups: Set[str]) -> RecatRow:
    """
    Parse and validate a single CSV row.
    Returns (groupname, category, subcategory, row_number) if valid, otherwise exits with error.
    """
    if row.get("__extra__"):
        _exit_with_error(None, "Data error in row {}: too many columns: {}".format(row_number, row["__extra__"]))

    groupname = (row.get("groupname") or "").strip()
    category_raw = (row.get("category") or "").strip()
    subcategory_raw = (row.get("subcategory") or "").strip()

    if groupname == "":
        _exit_with_error(None, "Data error in row {}: missing groupname".format(row_number))
    if not groupname.startswith("research-"):
        _exit_with_error(
            None,
            "Data error in row {}: '{}' is not a research group (must start with 'research-')".format(row_number, groupname),
        )

    if groupname in seen_groups:
        _exit_with_error(None, "Data error in row {}: duplicate groupname '{}' in CSV".format(row_number, groupname))
    seen_groups.add(groupname)

    category = _normalize_category(category_raw)
    subcategory = subcategory_raw.strip()

    if category == "":
        _exit_with_error(None, "Data error in row {}: missing category (mandatory)".format(row_number))

    if not yoda_names.is_valid_category(category):
        _exit_with_error(None, "Data error in row {}: '{}' is not a valid category name".format(row_number, category))

    if subcategory not in ("", None) and not yoda_names.is_valid_subcategory(subcategory):
        _exit_with_error(None, "Data error in row {}: '{}' is not a valid subcategory name".format(row_number, subcategory))

    return (groupname, category, subcategory, row_number)


def parse_csv_file_recat(input_file: str) -> List[RecatRow]:
    """
    Parse a CSV with required headers:
      groupname, category, subcategory
    """
    extracted_data: List[RecatRow] = []

    with open(input_file, mode="r", encoding="utf-8-sig", newline="") as csv_file:
        dialect = _sniff_csv_dialect_or_exit(csv_file)

        reader = csv.DictReader(
            csv_file,
            dialect=dialect,
            restkey="__extra__",
            restval="",
        )

        if reader.fieldnames is None:
            _exit_with_error(None, "CSV file is empty")
        else:
            header = _normalize_header(reader.fieldnames)
            reader.fieldnames = header
            _validate_header(header)

        seen_groups: Set[str] = set()
        for row in reader:
            row_number = reader.line_num
            if _is_effectively_empty_row(row):
                continue
            extracted_data.append(_parse_and_validate_row(row, row_number, seen_groups))

    return extracted_data


def _normalize_category(value: str) -> str:
    return (value or "").strip().lower().replace(".", "")


def _split_datamanagers(value: str) -> List[str]:
    """Split a ';'-separated datamanager list into entries."""
    if value is None:
        return []
    value = value.strip()
    if value == "":
        return []
    parts = [p.strip() for p in value.split(";")]
    return [p for p in parts if p != ""]


def _get_csv_possible_labels() -> List[str]:
    return ["groupname", "category", "subcategory"]


def _get_csv_required_labels() -> List[str]:
    return ["groupname", "category", "subcategory"]


def print_parsed_data(data: Sequence[RecatRow]) -> None:
    print("Parsed data:\n")
    for (groupname, category, subcategory, row_number) in data:
        print("Row: {}".format(row_number))
        print("Group: {}".format(groupname))
        print("New category: {}".format(category))
        print("New subcategory: {}".format(subcategory if subcategory else "(unchanged)"))
        print()


# ============================================================================
# CSV validation and applying changes
# ============================================================================

def _ensure_rodsadmin(session) -> None:
    """Exit unless the script user is a rodsadmin."""
    username = getattr(session, "username", None)
    if not username:
        _exit_with_error(session, "Could not determine connected iRODS username (session.username missing).")

    rows = list(session.query(User.type).filter(User.name == username).get_results())
    user_type = rows[0][User.type]
    if user_type != "rodsadmin":
        _exit_with_error(session, "Permission denied: '{}' is '{}' (requires rodsadmin).".format(username, user_type))


def _run_online_checks(session, rule_interface: RuleInterface, args: argparse.Namespace, data: Sequence[RecatRow]) -> None:
    """Online validation without making changes."""
    for username in sorted(set(args.datamanagers_new_category or [])):
        try:
            exists = rule_interface.call_rule_user_exists(username)
        except Exception as e:
            _exit_with_error(session, "Could not verify existence of user '{}': {}".format(username, e))
        if not exists:
            _exit_with_error(session, "Datamanager user '{}' does not exist in iRODS".format(username))

    for (groupname, category, subcategory, row_number) in data:
        _log(args, "Row {}: checking {}".format(row_number, groupname))

        if not common_queries.group_exists(session, groupname):
            _exit_with_error(session, "Data error in row {}: group '{}' does not exist".format(row_number, groupname))

        old_category = _get_group_metadata_single(session, groupname, "category")
        pending_collection = _get_pending_collection_path(session.zone, groupname, old_category)
        if collection_exists(session, pending_collection):
            _warn(
                "Row {}: pending/unprocessed publications found for datamanager-{} (collection {}). Row would be skipped.".format(
                    row_number, old_category, pending_collection
                )
            )


class ApplyResult:
    """What a run actually changed, it can be verified afterwards."""

    def __init__(self) -> None:
        self.applied: List[Tuple[str, str, str]] = []      # (groupname, category, subcategory)
        self.skipped: List[Tuple[int, str, str]] = []      # (row_number, groupname, reason)
        self.created_datamanager_groups: List[str] = []    # category names

    def categories_touched(self) -> List[str]:
        return sorted({category for (_, category, _) in self.applied})


def _apply_data(session, rule_interface: RuleInterface, args: argparse.Namespace,
                data: Sequence[RecatRow]) -> ApplyResult:
    result = ApplyResult()

    for (groupname, category, subcategory, row_number) in data:
        # Basic output (non-verbose)
        _basic(args, "Row {}: processing {}".format(row_number, groupname))

        # Verbose logging
        _log(args, "Row {}: {}".format(row_number, groupname))

        if not common_queries.group_exists(session, groupname):
            _exit_with_error(session, "Data error in row {}: group '{}' does not exist".format(row_number, groupname))
        if not groupname.startswith("research-"):
            _exit_with_error(session, "Data error in row {}: '{}' is not a research group".format(row_number, groupname))

        old_category = _get_group_metadata_single(session, groupname, "category")
        pending_collection = _get_pending_collection_path(session.zone, groupname, old_category)
        if collection_exists(session, pending_collection):
            _warn(
                "Row {}: pending/unprocessed publications found for datamanager-{} (collection {}). Skipping row.".format(
                    row_number, old_category, pending_collection
                )
            )
            _basic(args, "Row {}: skipped (pending/unprocessed publications in old category '{}')".format(row_number, old_category))
            result.skipped.append(
                (row_number, groupname,
                 "pending/unprocessed publications in old category '{}': {}".format(
                     old_category, pending_collection))
            )
            continue

        dm_groupname = "datamanager-{}".format(category)

        # Plan (verbose)
        _log(
            args,
            "  Plan: set category='{}'{}; ensure datamanager group exists: {}".format(
                category,
                ", subcategory='{}'".format(subcategory) if subcategory else "",
                dm_groupname,
            ),
        )

        if args.dry_run:
            _log(args, "  Dry-run: no changes executed for this row.")
            if not common_queries.group_exists(session, dm_groupname):
                _log(
                    args,
                    "  Dry-run: would create {} and assign managers: {}".format(
                        dm_groupname,
                        ";".join(args.datamanagers_new_category) if args.datamanagers_new_category else "(none)",
                    ),
                )
            else:
                _log(args, "  Dry-run: {} already exists (no membership changes performed by this script).".format(dm_groupname))

            _basic(args, "Row {}: dry-run OK (no changes)".format(row_number))
            continue

        _update_group_category_subcategory(rule_interface, groupname, category, subcategory, args)

        created = _ensure_datamanager_group_and_assign_managers_if_created(
            session=session,
            rule_interface=rule_interface,
            category=category,
            datamanagers=args.datamanagers_new_category,
            row_number=row_number,
            args=args,
        )

        result.applied.append((groupname, category, subcategory))
        if created:
            result.created_datamanager_groups.append(category)

        # Basic output (non-verbose)
        _basic(
            args,
            "Row {}: processed {} -> category='{}'{}".format(
                row_number,
                groupname,
                category,
                ", subcategory='{}'".format(subcategory) if subcategory else "",
            ),
        )

    return result


def _get_pending_collection_path(zone: str, groupname: str, old_category: str) -> str:
    if not groupname.startswith("research-"):
        raise ValueError(
            "Invalid groupname '{}': only groups starting with 'research-' are supported for now".format(groupname)
        )
    suffix = groupname[len("research-"):]  # research-xxx -> vault-xxx
    return "/{}/home/datamanager-{}/vault-{}".format(zone, old_category, suffix)


def _update_group_category_subcategory(
    rule_interface: RuleInterface,
    groupname: str,
    category: str,
    subcategory: str,
    args: argparse.Namespace,
) -> None:
    """Update category always; update subcategory only if provided."""
    _call_group_modify(rule_interface, groupname, "category", category, args)

    if subcategory is not None and subcategory != "":
        _call_group_modify(rule_interface, groupname, "subcategory", subcategory, args)


def _call_group_modify(
    rule_interface: RuleInterface,
    groupname: str,
    prop: str,
    value: str,
    args: argparse.Namespace,
) -> None:
    """Call uuGroupModify and handle success/error reporting."""
    status, msg = rule_interface.call_uuGroupModify(groupname, prop, value)

    if status == "0":
        _log(args, "  Updated {}: {}='{}'".format(groupname, prop, value))
        return

    print("Error while attempting to update group {}: {}='{}'".format(groupname, prop, value), file=sys.stderr)
    print("Status: {} , Message: {}".format(status, msg), file=sys.stderr)
    raise Exception("uuGroupModify failed for group={}, property={}".format(groupname, prop))


# ============================================================================
# Create dmgroup and assign dms
# ============================================================================

_ALREADY_EXISTS_CODES = {"-1089000", "-809000", "-806000"}


def _datamanager_groupname(category: str) -> str:
    return "datamanager-{}".format(category)


def _ensure_datamanager_group_exists(
    session,
    rule_interface: RuleInterface,
    category: str,
    row_number: int,
    args: argparse.Namespace,
) -> bool:
    """Ensure datamanager-<category> exists."""
    dm_groupname = _datamanager_groupname(category)

    _log(args, "  Ensuring datamanager group exists: {}".format(dm_groupname))

    if common_queries.group_exists(session, dm_groupname):
        _log(args, '  Notice: datamanager group "{}" already exists (no membership changes)'.format(dm_groupname))
        return False

    description = ""
    data_classification = ""
    schema_id = ""
    expiration_date = ""

    # A datamanager group is filed under its own category, and subcategory
    # E.g, category: <category>, subcategory: <category>, dmgroup: datamanger-<category>
    subcategory_for_add = category

    status, msg = rule_interface.call_uuGroupAdd(
        dm_groupname,
        category,
        subcategory_for_add,
        description,
        data_classification,
        schema_id,
        expiration_date,
        args.create_sram_co
    )

    if status in _ALREADY_EXISTS_CODES:
        _log(args, '  Notice: datamanager group "{}" already exists'.format(dm_groupname))
        return False

    if status != "0":
        raise Exception(
            'Error while attempting to create datamanager group "{}" (row {}). Status/message: {} / {}'.format(
                dm_groupname, row_number, status, msg
            )
        )

    _log(args, '  Created datamanager group "{}"'.format(dm_groupname))
    return True


def _ensure_user_is_manager(
    rule_interface: RuleInterface,
    dm_groupname: str,
    username: str,
    row_number: int,
    args: argparse.Namespace,
) -> None:
    """
    Ensure the user is a manager of the dmgroup.
    Add user if not present, then set role to manager.
    """
    currentrole = rule_interface.call_uuGroupGetMemberType(dm_groupname, username)

    if currentrole == "none":
        status, msg = rule_interface.call_uuGroupUserAdd(dm_groupname, username)
        if status != "0":
            _warn(
                "Row {}: could not add user {} to group {} (status/message: {} / {})".format(
                    row_number, username, dm_groupname, status, msg
                )
            )
            return
        currentrole = "member"
        _log(args, "  Notice: added user {} to group {}".format(username, dm_groupname))
    else:
        _log(args, "  Notice: user {} already present in {}".format(username, dm_groupname))

    requested_role = "manager"
    if are_roles_equivalent(requested_role, currentrole):
        _log(args, "  Notice: user {} already has role {} in {}".format(username, requested_role, dm_groupname))
        return

    status, msg = rule_interface.call_uuGroupUserChangeRole(dm_groupname, username, requested_role)
    if status == "0":
        _log(args, "  Notice: changed role of {} in {} to {}".format(username, dm_groupname, requested_role))
    else:
        _warn(
            "Row {}: could not change role of {} in {} to {} (status/message: {} / {})".format(
                row_number, username, dm_groupname, requested_role, status, msg
            )
        )


def _assign_managers_to_new_datamanager_group(
    rule_interface: RuleInterface,
    dm_groupname: str,
    datamanagers: List[str],
    row_number: int,
    args: argparse.Namespace,
) -> None:
    """
    Assign datamanagers as managers to the created dmgroup.
    """

    datamanagers_unique = sorted(set(datamanagers or []))

    _log(
        args,
        "  Assigning managers to {}: {}".format(
            dm_groupname,
            ";".join(datamanagers_unique) if datamanagers_unique else "(none)",
        ),
    )

    for username in datamanagers_unique:
        _ensure_user_is_manager(rule_interface, dm_groupname, username, row_number, args)


def _ensure_datamanager_group_and_assign_managers_if_created(
    session,
    rule_interface: RuleInterface,
    category: str,
    datamanagers: List[str],
    row_number: int,
    args: argparse.Namespace,
) -> bool:
    """
    Ensure the datamanager group exists.

    If it does not exist, create it and assign the provided datamanagers as managers.
    If it already exists, do not alter membership/roles.

    Returns True if the group was created by this call.
    """
    created = _ensure_datamanager_group_exists(
        session=session,
        rule_interface=rule_interface,
        category=category,
        row_number=row_number,
        args=args,
    )
    if not created:
        return False

    dm_groupname = _datamanager_groupname(category)
    _assign_managers_to_new_datamanager_group(
        rule_interface=rule_interface,
        dm_groupname=dm_groupname,
        datamanagers=datamanagers,
        row_number=row_number,
        args=args,
    )
    return True


def are_roles_equivalent(role1: str, role2: str) -> bool:
    """Match the same behaviour used in importgroups.py."""
    if role1 == role2:
        return True
    if (role1 == "normal" and role2 == "member") or (role1 == "member" and role2 == "normal"):
        return True
    return False


def _get_group_metadata_single(session, groupname: str, attributename: str) -> str:
    """
    Derived from groupinfo.py.
    To get a single-valued metadata attribute for a group.
    Raises if not found or multiple values found.
    """
    meta = list(
        session.query(UserMeta.value)
        .filter(Group.name == groupname)
        .filter(UserMeta.name == attributename)
        .get_results()
    )
    if len(meta) == 0:
        raise Exception("Attribute {} not found".format(attributename))
    if len(meta) > 1:
        raise Exception("Attribute {} has multiple values".format(attributename))
    return meta[0][UserMeta.value]


def _get_group_metadata_optional(session, groupname: str, attributename: str) -> Optional[str]:
    """Return a single-valued group attribute, or None when it is absent or ambiguous."""
    try:
        return _get_group_metadata_single(session, groupname, attributename)
    except Exception:
        return None


# ============================================================================
# Post-run verification
# ============================================================================

def _verify_changes(session, rule_interface: RuleInterface, args: argparse.Namespace,
                    result: ApplyResult) -> Tuple[List[str], List[str]]:
    """
    Re-read from iRODS what the run was supposed to change.
    Returns (problems, notes). Problems mean the run did not do what was asked.
    """
    problems: List[str] = []
    notes: List[str] = []

    for (groupname, category, subcategory) in result.applied:
        problems.extend(_verify_group_metadata(session, groupname, category, subcategory))

    for category in result.categories_touched():
        dm_groupname = _datamanager_groupname(category)

        if category not in result.created_datamanager_groups:
            notes.append(_describe_existing_datamanager_group(session, rule_interface, args, category))
            continue

        problems.extend(_verify_group_metadata(session, dm_groupname, category, category))
        problems.extend(_verify_datamanager_members(rule_interface, dm_groupname, args))

    return problems, notes


def _describe_existing_datamanager_group(session, rule_interface: RuleInterface,
                                         args: argparse.Namespace, category: str) -> str:
    """
    Describe a datamanager group this run did not create.

    This script deliberately never modifies an existing datamanager group: 
    Due to publications may still exist in original dm group, and AVUs may 
    be changed after recreation. it can be done by hand in the portal group manager.
    """
    dm_groupname = _datamanager_groupname(category)

    if not common_queries.group_exists(session, dm_groupname):
        return "no datamanager group exists for category '{}'".format(category)

    lines = ["{} already existed and was not modified".format(dm_groupname)]

    if not _get_group_metadata_optional(session, dm_groupname, "subcategory"):
        lines.append("it has no subcategory, so the portal will not display it")

    not_managing = _datamanagers_not_managing(rule_interface, dm_groupname, args)
    if not_managing:
        lines.append("not added as manager: {}".format(", ".join(not_managing)))

    if len(lines) > 1:
        lines.append("adjust this group manually in the portal group manager if needed")

    return "\n".join(lines)


def _datamanagers_not_managing(rule_interface: RuleInterface, dm_groupname: str,
                               args: argparse.Namespace) -> List[str]:
    """Which of the requested datamanagers do not already manage this group."""
    not_managing = []

    for username in sorted(set(args.datamanagers_new_category or [])):
        try:
            role = rule_interface.call_uuGroupGetMemberType(dm_groupname, username)
        except Exception:
            # Reporting only.
            continue
        if not are_roles_equivalent("manager", role):
            not_managing.append(username)

    return not_managing


def _verify_group_metadata(session, groupname: str, category: str, subcategory: str) -> List[str]:
    """Check that a group carries the expected category and subcategory."""
    problems: List[str] = []

    actual_category = _get_group_metadata_optional(session, groupname, "category")
    if actual_category != category:
        problems.append("{}: category is {}, expected '{}'".format(
            groupname, _quote_or_missing(actual_category), category))

    # An empty subcategory in the CSV means "leave unchanged", so there is
    # nothing to verify for it.
    if subcategory:
        actual_subcategory = _get_group_metadata_optional(session, groupname, "subcategory")
        if actual_subcategory != subcategory:
            problems.append("{}: subcategory is {}, expected '{}'".format(
                groupname, _quote_or_missing(actual_subcategory), subcategory))

    return problems


def _verify_datamanager_members(rule_interface: RuleInterface, dm_groupname: str,
                                args: argparse.Namespace) -> List[str]:
    """Check that every datamanager passed on the command line manages the new group."""
    problems: List[str] = []

    for username in sorted(set(args.datamanagers_new_category or [])):
        try:
            role = rule_interface.call_uuGroupGetMemberType(dm_groupname, username)
        except Exception as e:
            problems.append("{}: could not read role of {} ({})".format(dm_groupname, username, e))
            continue
        if not are_roles_equivalent("manager", role):
            problems.append("{}: {} has role '{}', expected 'manager'".format(
                dm_groupname, username, role))

    return problems


def _quote_or_missing(value: Optional[str]) -> str:
    return "missing" if value is None else "'{}'".format(value)


def _report_result(args: argparse.Namespace, result: ApplyResult, problems: Sequence[str],
                   notes: Sequence[str]) -> None:
    """Print the end-of-run summary. Always printed, verbose or not."""
    print("")
    print("Summary: {} group(s) recategorized, {} datamanager group(s) created, {} row(s) skipped".format(
        len(result.applied), len(set(result.created_datamanager_groups)), len(result.skipped)
    ))

    for (row_number, groupname, reason) in result.skipped:
        print("  Skipped row {}: {} ({})".format(row_number, groupname, reason))

    for note in notes:
        first_line, _, remainder = note.partition("\n")
        print("  Note: {}".format(first_line))
        for line in remainder.splitlines():
            print("        {}".format(line))

    if problems:
        print("")
        sys.stdout.flush()
        print("Verification FAILED - the following changes did not take effect:", file=sys.stderr)
        for problem in problems:
            print("  {}".format(problem), file=sys.stderr)
        return

    if result.applied:
        print("Verification OK: all changes confirmed in iRODS.")

    if result.skipped:
        print("Not every row was applied: the skipped group(s) are still in their original")
        print("category. Process the publications listed above, then re-run for those groups.")
