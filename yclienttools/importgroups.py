'''Creates a list of groups based on a CSV file'''
import argparse
import csv
import sys
from typing import List, Set, Tuple

from iteration_utilities import duplicates, unique_everseen

from yclienttools import common_args, common_config

from yclienttools import session as s
from yclienttools.common_rules import RuleInterface
from yclienttools.exceptions import SizeNotSupportedException
from yclienttools import yoda_names

# Based on yoda-batch-add script by Ton Smeele


def parse_csv_file(input_file: str, args: argparse.Namespace, yoda_version: str) -> list:
    extracted_data = []

    with open(input_file, mode="r", encoding="utf-8-sig") as csv_file:

        try:
            dialect = csv.Sniffer().sniff(csv_file.read(), delimiters=';,')
        except Exception:
            _exit_with_error('CSV is not correctly delimited with ";" or ","')

        csv_file.seek(0)

        reader = csv.reader(
            csv_file,
            dialect=dialect,
        )
        header = next(reader)
        row_number = 1  # header row already read

        for label in _get_csv_required_labels():
            if label not in header:
                _exit_with_error(
                    'CSV header is missing compulsory field "{}"'.format(label))

        # Check that all header names are valid
        possible_labels = _get_csv_possible_labels(yoda_version)
        labels_with_optional_suffix = ['viewer', 'member', 'manager']
        for label in header:
            if label not in possible_labels:
                found_match = False
                for opt_label in labels_with_optional_suffix:
                    if label.startswith('{}:'.format(opt_label)):
                        found_match = True

                if not found_match:
                    _exit_with_error(
                        'CSV header contains unknown field "{}"'.format(label))

        duplicate_columns = _get_duplicate_columns(header, yoda_version)
        if (len(duplicate_columns) > 0):
            _exit_with_error(
                "File has duplicate column(s): " + str(duplicate_columns))

        # Create a kind of MultiDict.
        # keys are the column names, items are the list of items
        for line in reader:
            row_number += 1
            d: dict = {}
            for j in range(len(line)):
                item = line[j].strip()
                if len(item):
                    if header[j] not in d:
                        d[header[j]] = []

                    d[header[j]].append(item)

            rowdata, error = _process_csv_line(d, args, yoda_version)

            if error is None:
                extracted_data.append(rowdata)
            else:
                _exit_with_error("Data error in row {}: {}".format(
                    str(row_number), error))

    return extracted_data


def _get_csv_possible_labels(yoda_version: str) -> List[str]:
    if yoda_version in ('1.7', '1.8'):
        return ['category', 'subcategory', 'groupname', 'viewer', 'member', 'manager']
    else:
        return ['category', 'subcategory', 'groupname', 'viewer', 'member', 'manager', 'expiration_date', 'schema_id']


def _get_csv_required_labels() -> List[str]:
    return ['category', 'subcategory', 'groupname']


def _get_csv_1_9_exclusive_labels() -> List[str]:
    """Returns labels that can only appear with yoda version 1.9 and higher."""
    return ['expiration_date', 'schema_id']


def _get_csv_predefined_labels(yoda_version: str) -> List[str]:
    if yoda_version in ('1.7', '1.8'):
        return ['category', 'subcategory', 'groupname']
    else:
        return ['category', 'subcategory', 'groupname', 'expiration_date', 'schema_id']


def _get_duplicate_columns(fields_list: List[str], yoda_version: str) -> Set[str]:
    """ Only checks columns that cannot have duplicates """
    fields_seen = set()
    duplicate_fields = set()

    for field in fields_list:
        if (field in _get_csv_predefined_labels(yoda_version)):
            if field in fields_seen:
                duplicate_fields.add(field)
            else:
                fields_seen.add(field)

    return duplicate_fields


def _get_duplicate_groups(row_data: list) -> List[str]:
    group_names = list(map(lambda r: r[2], row_data))
    return list(unique_everseen(duplicates(group_names)))


def _process_csv_line(line: dict, args: argparse.Namespace, yoda_version: str) -> Tuple:
    if ('category' not in line or not len(line['category'])
            or 'subcategory' not in line or not len(line['subcategory'])
            or 'groupname' not in line or not len(line['groupname'])):
        return None, "Row has a missing group name, category or subcategory"

    category = line['category'][0].strip().lower().replace('.', '')
    subcategory = line['subcategory'][0].strip()
    groupname = "research-" + line['groupname'][0].strip().lower()
    schema_id = line['schema_id'][0] if 'schema_id' in line and len(line['schema_id']) else ''
    expiration_date = line['expiration_date'][0] if 'expiration_date' in line and len(line['expiration_date']) else ''
    managers = []
    members = []
    viewers = []

    for column_name, item_list in line.items():
        if column_name == '':
            return None, 'Column cannot have an empty label'
        elif yoda_version in ('1.7', '1.8') and column_name in _get_csv_1_9_exclusive_labels():
            return None, 'Column "{}" is only supported in Yoda 1.9 and higher'.format(column_name)
        elif column_name in _get_csv_predefined_labels(yoda_version):
            continue

        for i in range(len(item_list)):
            item_list[i] = item_list[i].strip().lower()
            is_valid, validation_message = yoda_names.is_valid_username(item_list[i], args.no_validate_domains)
            if not is_valid:
                return None, validation_message

        if column_name.lower() == 'manager' or column_name.lower().startswith('manager:'):
            managers.extend(item_list)
        elif column_name.lower() == 'member' or column_name.lower().startswith('member:'):
            members.extend(item_list)
        elif column_name.lower() == 'viewer' or column_name.lower().startswith('viewer:'):
            viewers.extend(item_list)

    # perform additional data validations
    if len(managers) == 0:
        return None, "Group must have a group manager"

    if not yoda_names.is_valid_category(category):
        return None, '"{}" is not a valid category name.'.format(category)

    if not yoda_names.is_valid_category(subcategory):
        return None, '"{}" is not a valid subcategory name.'.format(subcategory)

    if not yoda_names.is_valid_groupname(groupname):
        return None, '"{}" is not a valid group name.'.format(groupname)

    if not yoda_names.is_valid_schema_id(schema_id):
        return None, '"{}" is not a valid schema id.'.format(schema_id)

    if not yoda_names.is_valid_expiration_date(expiration_date):
        return None, '"{}" is not a valid expiration date.'.format(expiration_date)

    row_data = (category, subcategory, groupname, managers,
                members, viewers, schema_id, expiration_date)
    return row_data, None


def _are_roles_equivalent(a: str, b: str) -> bool:
    """Checks whether two roles are equivalent. Needed because Yoda and Yoda-clienttools
       use slightly different names for the roles."""
    r_role_names = ["viewer", "reader"]
    m_role_names = ["member", "normal"]

    if a == b:
        return True
    elif a in r_role_names and b in r_role_names:
        return True
    elif a in m_role_names and b in m_role_names:
        return True
    else:
        return False


def validate_data(rule_interface: RuleInterface, args: argparse.Namespace, data: list) -> List[str]:
    errors = []
    for (category, subcategory, groupname, managers, members, viewers, schema_id, expiration_date) in data:
        if rule_interface.call_uuGroupExists(groupname) and not args.allow_update:
            errors.append('Group "{}" already exists'.format(groupname))

        for user in managers + members + viewers:
            if not yoda_names.is_internal_user(user, args.internal_domains.split(",")):
                # ensure that external users already have an iRODS account
                # we do not want to be the actor that creates them (unless
                # we are creating them in the name of a creator user)
                if not rule_interface.call_rule_user_exists(user) and not args.creator_user:
                    errors.append(
                        'Group {} has nonexisting external user {}'.format(groupname, user))

    return errors


def apply_data(rule_interface: RuleInterface, args: argparse.Namespace, data: list) -> None:
    for (category, subcategory, groupname, managers, members, viewers, schema_id, expiration_date) in data:
        new_group = False

        if args.verbose:
            print('Adding and updating group: {}'.format(groupname))

        # First create the group. Note that the rodsadmin actor will become a
        # groupmanager.
        [status, msg] = rule_interface.call_uuGroupAdd(
            groupname, category, subcategory, '', 'unspecified', schema_id, expiration_date)

        if ((status in '-1089000', '-809000', '-806000')) and args.allow_update:
            print(
                'WARNING: group "{}" not created, it already exists'.format(groupname))
            if schema_id != '':
                print(
                    'WARNING: group property "schema_id" not updated, as it can only be specified when the group is first created')
        elif status != '0':
            _exit_with_error(
                'Error while attempting to create group "{}". Status/message: {} / {}'.format(
                    groupname,
                    status,
                    msg))
        else:
            new_group = True

        # Now add the users and set their role if other than member
        allusers = managers + members + viewers
        for username in list(set(allusers)):   # duplicates removed
            currentrole = rule_interface.call_uuGroupGetMemberType(
                groupname, username)

            if currentrole == "none":
                if args.creator_user:
                    [status, msg] = rule_interface.call_uuGroupUserAddByOtherCreator(
                        groupname, username, args.creator_user, args.creator_zone)
                else:
                    [status, msg] = rule_interface.call_uuGroupUserAdd(
                        groupname, username)

                if status == '0':
                    currentrole = "member"
                    if args.verbose:
                        print("Notice: added user {} to group {}".format(
                            username, groupname))
                else:
                    print("Warning: error occurred while attempting to add user {} to group {}".format(
                        username,
                        groupname))
                    print("Status: {} , Message: {}".format(status, msg))
            else:
                if args.verbose:
                    print("Notice: user {} is already present in group {}.".format(
                        username, groupname))

            # Set requested role. Note that user could be listed in multiple roles.
            # In case of multiple roles, manager takes precedence over normal,
            # and normal over reader
            role = 'reader'
            if username in members:
                role = 'normal'
            if username in managers:
                role = 'manager'

            if _are_roles_equivalent(role, currentrole):
                if args.verbose:
                    print("Notice: user {} already has role {} in group {}.".format(
                        username, role, groupname))
            else:
                [status, msg] = rule_interface.call_uuGroupUserChangeRole(
                    groupname, username, role)
                if status == '0':
                    if args.verbose:
                        print("Notice: changed role of user {} in group {} to {}".format(
                            username, groupname, role))
                else:
                    print(
                        "Warning: error while attempting to change role of user {} in group {} to {}".format(
                            username,
                            groupname,
                            role))
                    print("Status: {} , Message: {}".format(status, msg))

        # Always remove the rods user for new groups, unless it is in the
        # CSV file.
        if (new_group and "rods" not in allusers
                and rule_interface.call_uuGroupGetMemberType(groupname, "rods") != "none"):
            (status, msg) = rule_interface.call_uuGroupUserRemove(groupname, "rods")
            if status == "0":
                if args.verbose:
                    print("Notice: removed rods user from group " + groupname)
            else:
                if status != 0:
                    print("Warning: error while attempting to remove user rods from group {}".format(
                        groupname))
                    print("Status: {} , Message: {}".format(status, msg))

        # Update expiration date if applicable
        if not new_group and expiration_date not in ['', '.'] and args.allow_update:
            [status, msg] = rule_interface.call_uuGroupModify(
                groupname, "expiration_date", expiration_date)
            if status == "0":
                if args.verbose:
                    print("Notice: updated expiration date to {} for group {}".format(
                        expiration_date, groupname))
            else:
                print("Warning: error while attempting to update expiration date to {} for group {}".format(
                    expiration_date, groupname))
                print("Status: {} , Message: {}".format(status, msg))

        # Remove users not in sheet
        if args.delete:

            try:
                currentusers = rule_interface.call_uuGroupGetMembers(groupname)
            except SizeNotSupportedException:
                print("Unable to check whether members of group {} need to be deleted.".format(
                    groupname))
                print("Number of current members group is too large.")
                continue

            currentusers = [user.split('#')[0] for user in currentusers]
            for user in currentusers:
                if user not in allusers:
                    if user in managers:
                        if len(managers) == 1:
                            print("Error: cannot remove user {} from group {}, because he/she is the only group manager".format(
                                user, groupname))
                            continue
                        else:
                            managers.remove(user)
                    if args.verbose:
                        print("Removing user {} from group {}".format(
                            user, groupname))
                    (status, msg) = rule_interface.call_uuGroupUserRemove(
                        groupname, user)
                    if status != "0":
                        print("Warning: error while attempting to remove user {} from group {}".format(
                            user, groupname))
                        print("Status: {} , Message: {}".format(status, msg))


def print_parsed_data(data: list) -> None:
    print('Parsed data:')
    print()

    if data is None:
        print('No data loaded')
    else:
        for (category, subcategory, groupname,
             managers, members, viewers, schema_id, expiration_date) in data:
            print("Category: {}".format(category))
            print("Subcategory: {}".format(subcategory))
            print("Group: {}".format(groupname))
            print("Managers: {}".format(','.join(managers)))
            print("Members: {}".format(','.join(members)))
            print("Readonly members: {}".format(','.join(viewers)))
            print("Schema Id: {}".format(schema_id))
            print("Expiration Date: {}".format(expiration_date))
            print()


def entry() -> None:
    '''Entry point'''
    args = _get_args()
    yoda_version = args.yoda_version if args.yoda_version is not None else common_config.get_default_yoda_version()
    data = parse_csv_file(args.csvfile, args, yoda_version)

    if args.offline_check or args.verbose:
        print_parsed_data(data)

    if args.delete and not args.allow_update:
        _exit_with_error(
            "Using the --delete option without the --allow-update option is not supported.")

    if (args.creator_user and not args.creator_zone) or (not args.creator_user and args.creator_zone):
        _exit_with_error(
            "Using the --creator-user option without the --creator-zone option is not supported.")

    if (args.creator_user and (yoda_version in ('1.7', '1.8'))):
        _exit_with_error(
            "The --creator-user and --creator-zone options are only supported with Yoda versions 1.9 and higher.")

    duplicate_groups = _get_duplicate_groups(data)
    if duplicate_groups:
        _exit_with_error(
            "The group list has multiple rows with the same group name(s): " + ",".join(duplicate_groups))

    if args.offline_check:
        sys.exit(0)

    session = s.setup_session(yoda_version)
    rule_interface = RuleInterface(session, yoda_version)

    try:
        validation_errors = validate_data(rule_interface, args, data)

        if len(validation_errors) > 0:
            _exit_with_validation_errors(validation_errors)

        if not args.online_check:
            apply_data(rule_interface, args, data)

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)

    finally:
        session.cleanup()


def _get_args() -> argparse.Namespace:
    '''Parse command line arguments'''

    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=_get_format_help_text(),
        formatter_class=argparse.RawTextHelpFormatter)
    common_args.add_default_args(parser)
    parser.add_argument('csvfile', help='Name of the CSV file')
    parser.add_argument('-i', '--internal-domains', required=True,
                        help='Comma-separated list of internal email domains to the Yoda server, or "all" if all domains should be considered internal')
    actiongroup = parser.add_mutually_exclusive_group()
    actiongroup.add_argument('--offline-check', '-c', action='store_true',
                             help='Check mode (offline): verify CSV format only. Does not connect to iRODS and does not create groups')
    actiongroup.add_argument('--online-check', '-C', action='store_true',
                             help='Check mode (online): verify CSV format and that groups do not exist. Does not create groups.')
    parser.add_argument('--allow-update', "-u", action='store_true', default=False,
                        help='Allows existing groups to be updated')
    parser.add_argument('--delete', '-d', action='store_true', default=False,
                        help='Delete group members not in CSV file')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show information as extracted from CSV file')
    parser.add_argument('--no-validate-domains', '-n', action='store_true',
                        help='Do not validate email address domains')
    parser.add_argument('--creator-user', type=str,
                        help='User who creates user (only available in Yoda 1.9 and higher)')
    parser.add_argument('--creator-zone', type=str,
                        help='Zone of the user who creates user (only available in Yoda 1.9 and higher)')
    return parser.parse_args()


def _get_format_help_text() -> str:
    return '''
        The CSV file is expected to include the following labels in its header (the first row):
        'category'        = category for the group
        'subcategory'     = subcategory for the group
        'groupname'       = name of the group (without the "research-" prefix)

        For Yoda versions 1.9 and higher, these labels can optionally be included:
        'expiration_date' = expiration date for the group. Can only be set when the group is first created.
        'schema_id'       = schema id for the group. Can only be set when the group is first created.

        The remainder of the columns should be labels that indicate the role of each group member:
        'manager'         = user that will be given the role of manager
        'member'          = user that will be given the role of member with read/write
        'viewer'          = user that will be given the role of viewer with read

        Notes:
        - Columns may appear in any order
        - Empty data cells are ignored: groups can differ in number of members
        - manager, member, and viewer columns can appear multiple times

        Example:
        category,subcategory,groupname,manager,member,member
        departmentx,teama,groupteama,m.manager@example.com,m.member@example.com,n.member@example.com
        departmentx,teamb,groupteamb,m.manager@example.com,p.member@example.com,

        Example Yoda 1.9 and higher:
        category,subcategory,groupname,manager,member,expiration_date,schema_id
        departmentx,teama,groupteama,m.manager@example.com,m.member@example.com,2055-01-01,default-3
        departmentx,teamb,groupteamb,m.manager@example.com,p.member@example.com,,
    '''


def _exit_with_error(message: str) -> None:
    print("Error: {}".format(message), file=sys.stderr)
    sys.exit(1)


def _exit_with_validation_errors(errors: List[str]) -> None:
    for error in errors:
        print("Validation error: {}".format(error), file=sys.stderr)
    sys.exit(1)
