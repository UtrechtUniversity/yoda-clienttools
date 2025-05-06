import argparse
import csv
import sys
from typing import List, Tuple

from irods.session import iRODSSession
from irods.models import Collection, DataObject
from irods.column import Like

from yclienttools import session as s
from yclienttools.common_config import get_default_yoda_version
from yclienttools.common_queries import get_vault_data_packages, collection_exists


def entry():
    """Entry point"""
    try:
        args = _get_args()
        yoda_version = args.yoda_version or get_default_yoda_version()
        session = s.setup_session(yoda_version, session_timeout=600)
        report_dataduplication(args, session)
        session.cleanup()
    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)


def _get_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-e", "--environment", type=str, default=None,
                        help="Optional environment label to include in the output")
    parser.add_argument("--yoda-version", type=str, default=None,
                        help="Optional Yoda version (default defined in config)")
    return parser.parse_args()


def _get_output_columns(args: argparse.Namespace) -> List[str]:
    """Determines output CSV column headers based on the presence of the environment flag."""
    columns = [
        "Vault Group",
        "Data Package Collection",
        "Research Group",
        "Research Collection Path",
        "Research Package Match"
    ]
    return columns if args.environment is None else ["Environment"] + columns


def _get_research_group_name(vault_group: str) -> str:
    """Converts a vault group name to the corresponding research group name."""
    return vault_group.replace("vault", "research")


def _get_research_group_path(zone: str, research_group: str) -> str:
    """Constructs the full iRODS path to the research group name."""
    return f"/{zone}/home/{research_group}"


def _extract_collection_name(data_package_name: str) -> str:
    """Extracts the base collection name from a data package name."""
    return data_package_name.split("[")[0]


def _find_potential_research_matches(session: iRODSSession, research_coll_path: str, collection: str) -> List[str]:
    """Finds candidate research collections that could match a given data package."""
    if research_coll_path.split('/')[-1] == collection:
        search_pattern = f"{research_coll_path}"
    else:
        search_pattern = f"{research_coll_path}/%{collection}"

    results = session.query(Collection.name).filter(
        Like(Collection.name, search_pattern)
    ).get_results()

    return [row[Collection.name] for row in results]


def _get_collection_file_stats(session: iRODSSession, coll_path: str, is_vault_package: bool) -> Tuple[int, int]:
    """Gets the number of files and total size for a given collection."""
    file_count = 0
    total_size = 0
    original_path = f"{coll_path}/original"

    scan_paths = [original_path] if is_vault_package and collection_exists(session, original_path) else [coll_path]

    if not is_vault_package:
        subcolls = session.query(Collection.name).filter(
            Collection.parent_name == coll_path
        ).get_results()
        scan_paths += [subcoll[Collection.name] for subcoll in subcolls]

    for path in scan_paths:
        results = list(session.query(DataObject.name, DataObject.size).filter(
            Collection.name == path
        ).get_results())
        file_count += len(results)
        total_size += sum(row[DataObject.size] for row in results)

    return file_count, total_size


def _files_are_identical(vault_files: int, vault_size: int, research_files: int, research_size: int) -> bool:
    """Checks if two collections (vault and research) are identical in file count and size."""
    return vault_files == research_files and vault_size == research_size


def report_dataduplication(args, session: iRODSSession):
    """
    Generate duplication report between vault and research collections.
    Outputs only matching pairs (files and size match).
    """
    writer = csv.DictWriter(sys.stdout, fieldnames=_get_output_columns(args), delimiter=',')
    writer.writeheader()

    data_packages = get_vault_data_packages(session)
    if not data_packages:
        print("No data packages found in any vault group.")
        return

    for coll_path in sorted(data_packages):
        if not _is_valid_collection_path(coll_path):
            continue

        zone, vault_group, data_package_name = _parse_collection_path(coll_path)
        research_group = _get_research_group_name(vault_group)
        research_coll_path = _get_research_group_path(zone, research_group)

        if not collection_exists(session, research_coll_path):
            continue

        collection = _extract_collection_name(data_package_name)
        research_matches = _find_potential_research_matches(session, research_coll_path, collection)

        if not research_matches:
            continue

        vault_files, vault_size = _get_collection_file_stats(session, coll_path, is_vault_package=True)

        matched_path = _find_matching_research_package(session, research_matches, vault_files, vault_size)
        if matched_path:
            _write_report_row(writer, args, vault_group, coll_path, research_group, research_coll_path, matched_path)


def _is_valid_collection_path(path: str) -> bool:
    """Validates that the collection path has the expected format with at least 4 parts."""
    parts = path.strip("/").split("/")
    return len(parts) >= 4


def _parse_collection_path(path: str) -> Tuple[str, str, str]:
    """Parses a full collection path into its zone, group, and data package name components."""
    parts = path.strip("/").split("/")
    return parts[0], parts[2], parts[3]


def _find_matching_research_package(session: iRODSSession, matches: List[str], vault_files: int, vault_size: int) -> str:
    """Scans a list of potential research collections and returns the one that matches the vault package."""
    for match_path in matches:
        research_files, research_size = _get_collection_file_stats(session, match_path, is_vault_package=False)
        if _files_are_identical(vault_files, vault_size, research_files, research_size):
            return match_path
    return ""


def _write_report_row(writer, args, vault_group, coll_path, research_group, research_coll_path, matched_path):
    """Writes a single row of duplication report to CSV output."""
    row = {
        "Vault Group": vault_group,
        "Data Package Collection": coll_path,
        "Research Group": research_group,
        "Research Collection Path": research_coll_path,
        "Research Package Match": matched_path
    }
    if args.environment:
        row["Environment"] = args.environment
    writer.writerow(row)
