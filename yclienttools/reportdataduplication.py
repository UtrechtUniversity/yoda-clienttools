import argparse
import csv
import sys
from typing import List, Dict, Tuple, Any, Set, Union

import humanize
from irods.session import iRODSSession
from irods.models import Collection, DataObject
from irods.column import Like

from yclienttools import common_args, session as s
from yclienttools.common_config import get_default_yoda_version
from yclienttools.common_queries import get_vault_data_packages, collection_exists, get_collection_size
from yclienttools.options import GroupByOption


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
    parser.add_argument("-s", "--size", default=False, action='store_true',
                        help='Include size of research/deposit collection, vault collection and revisions in output')
    parser.add_argument("-H", "--human-readable", default=False, action='store_true',
                        help='Report sizes in human-readable figures (only relevant in combination with --size parameter)')
    common_args.add_default_args(parser)
    return parser.parse_args()


def _get_output_columns(args: argparse.Namespace) -> List[str]:
    """Determines output CSV column headers based on the presence of the environment flag."""
    columns = ["Research Group", "Research Path", "Vault Path"]
    if args.environment:
        columns.insert(0, "Environment")
    if args.size:
        columns.append("Size")
    return columns


def _get_research_group_name(vault_group: str) -> str:
    """Converts a vault group name to its corresponding research group name."""
    return vault_group.replace("vault", "research", 1)


def _get_research_group_path(zone: str, research_group: str) -> str:
    """Construct the full iRODS path for a research group."""
    return f"/{zone}/home/{research_group}"


def _get_collection_name(data_package_name: str) -> str:
    """Get the base collection name from a data package name."""
    return data_package_name.split("[")[0]


def _size_to_str(value: Union[int, None], human_readable: bool) -> str:
    if value is None:
        return "N/A"
    elif human_readable:
        return humanize.naturalsize(value, binary=True)
    else:
        return str(value)


def _get_research_matches(session: iRODSSession, research_path: str, collection_name: str) -> List[str]:
    """
    Get research collections matching the given collection name under the research group.
    Includes:
    - Direct match: if research_path ends in the collection_name
    - Direct child: /research_path/collection_name
    - Nested subcollections ending in /collection_name
    """
    matches: Set[str] = set()

    # Match top-level
    if research_path.split('/')[-1] == collection_name:
        matches.add(research_path)

    # Match subcollections
    query = session.query(Collection.name).filter(
        Like(Collection.name, f"{research_path}/%"),
        Like(Collection.name, f"%/{collection_name}")
    )
    for row in query.get_results():
        matches.add(row[Collection.name])

    return sorted(matches)


def _get_collection_tree(session: iRODSSession, coll_path: str) -> Dict[str, Dict]:
    """
    Return a dict containing:
    - 'files': {relative_path: size}
    - 'subcollections': sorted list of relative paths of all subcollections
    """
    result: Dict[str, Any] = {
        "files": {},
        "subcollections": set()
    }

    # Include base collection if it exists
    if collection_exists(session, coll_path):
        result["subcollections"].add("")

    # Get all subcollections (even empty ones)
    query_subcolls = session.query(Collection.name).filter(
        Like(Collection.name, f"{coll_path}/%")
    )
    for row in query_subcolls.get_results():
        rel_coll_path = row[Collection.name].replace(coll_path, "", 1).lstrip("/")
        if rel_coll_path:
            result["subcollections"].add(rel_coll_path)

    # Get data objects in collection
    coll_data_objects = session.query(Collection.name, DataObject.name, DataObject.size).filter(
        Collection.name == coll_path
    )
    # Get all data objects in all subcollections
    subcoll_data_objects = session.query(Collection.name, DataObject.name, DataObject.size).filter(
        Like(Collection.name, f"{coll_path}/%")
    )

    all_data_objects = list(coll_data_objects.get_results()) + list(subcoll_data_objects.get_results())
    for row in all_data_objects:
        full_path = f"{row[Collection.name]}/{row[DataObject.name]}"
        rel_path = full_path.replace(coll_path, "", 1).lstrip("/")
        result["files"][rel_path] = row[DataObject.size]

    result["subcollections"] = sorted(result["subcollections"])
    return result


def are_collections_identical(session: iRODSSession, path1: str, path2: str) -> bool:
    """
    Check if two collections are structurally identical:
    - Same files (path + size)
    - Same subcollection structure
    """
    tree1 = _get_collection_tree(session, path1)
    tree2 = _get_collection_tree(session, path2)

    return (
        tree1["files"].keys() == tree2["files"].keys()
        and all(tree1["files"][k] == tree2["files"][k] for k in tree1["files"])
        and tree1["subcollections"] == tree2["subcollections"]
    )


def is_valid_collection_path(path: str) -> bool:
    """Ensure the collection path has at least 4 parts."""
    return len(path.strip("/").split("/")) >= 4


def parse_collection_path(path: str) -> Tuple[str, str, str]:
    """Parse an iRODS collection path into zone, group, and data package name."""
    parts = path.strip("/").split("/")
    return parts[0], parts[2], parts[3]


def collections_exist(session: iRODSSession, *paths: str) -> bool:
    """Check if all given collections exist."""
    return all(collection_exists(session, path) for path in paths)


def process_collection(session: iRODSSession, args: argparse.Namespace, coll_path: str) -> List[Dict[str, Any]]:
    """Process one vault collection and return any matching research collections."""
    matches: List[Dict[str, str]] = []

    if not is_valid_collection_path(coll_path):
        return matches

    zone, vault_group, data_package_name = parse_collection_path(coll_path)
    research_group = _get_research_group_name(vault_group)
    research_path = _get_research_group_path(zone, research_group)

    vault_original_path = f"{coll_path}/original"

    if not collections_exist(session, research_path, coll_path, vault_original_path):
        return matches

    collection_name = _get_collection_name(data_package_name)
    research_candidates = _get_research_matches(session, research_path, collection_name)

    for candidate in research_candidates:
        if are_collections_identical(session, vault_original_path, candidate):
            match: Dict[str, Any] = {
                'research_group': research_group,
                'research_path': candidate,
                'vault_path': coll_path
            }
            if args.size:
                match["size"] = _get_collection_size_for_ddr(session, candidate)
            matches.append(match)

    return matches


def _get_collection_size_for_ddr(session: iRODSSession, collection_name: str) -> int:
    return get_collection_size(session, collection_name, True, GroupByOption.none, False)['all']


def report_dataduplication(args: argparse.Namespace, session: iRODSSession):
    """Generate duplication report between vault and research collections."""
    writer = csv.DictWriter(sys.stdout, fieldnames=_get_output_columns(args), delimiter=',')
    writer.writeheader()

    data_packages = get_vault_data_packages(session)
    if not data_packages:
        print("No data packages found.", file=sys.stderr)
        return

    for coll_path in sorted(data_packages):
        try:
            for match in process_collection(session, args, coll_path):
                write_report_row(
                    args=args,
                    writer=writer,
                    match=match
                )
        except Exception as e:
            print(f"Error processing collection {coll_path}: {e}", file=sys.stderr)


def write_report_row(args: argparse.Namespace,
                     writer: csv.DictWriter,
                     match: Dict[str, Any]):
    """Write a single row of duplication report to CSV output."""
    row = {
        "Research Group": match["research_group"],
        "Research Path": match["research_path"],
        "Vault Path": match["vault_path"]
    }
    if args.environment:
        row["Environment"] = args.environment
    if args.size:
        row["Size"] = _size_to_str(match["size"], args.human_readable)
    try:
        writer.writerow(row)
    except Exception as e:
        print(f"Error writing row: {e}", file=sys.stderr)
