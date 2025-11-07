'''Prints a report for data objects that have a copy in both an intake vault group and one or more research groups (in CSV format).'''

import argparse
import sys
import os
import csv
from itertools import chain
from typing import Any, Dict, List

import humanize
from irods.column import Like
from irods.models import Collection, DataObject
from irods.session import iRODSSession

from yclienttools import common_args, session as s
from yclienttools.common_config import get_default_yoda_version
from yclienttools.common_queries import collection_exists


def entry() -> None:
    """Entry point"""
    args = _get_args()
    yoda_version = args.yoda_version or get_default_yoda_version()
    session = s.setup_session(yoda_version, session_timeout=600)

    try:
        intake_grps = parse_groups_file(args.intakefile)
        research_grps = parse_groups_file(args.researchfile)
        report_intake_duplication(args, session, intake_grps, research_grps)
    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)
    finally:
        session.cleanup()


def _get_args() -> argparse.Namespace:
    """Parses command line arguments"""
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=_get_format_help_text(),
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('intakefile', help='File name of the list of intake vault groups')
    parser.add_argument('researchfile', help='File name of the list of research groups')
    parser.add_argument('-H', '--human-readable', default=False, action='store_true',
                        help='Report sizes in human-readable figures')
    common_args.add_default_args(parser)
    return parser.parse_args()


def _get_format_help_text() -> str:
    return '''
        The input files should be text files. Each new line should be the name of a group with no separator (intake vault groups for 'intakefile', research groups for 'research file').

        Example file:
        research-core-0
        research-default-1
        research-initial
    '''


def parse_groups_file(file: str) -> List[str]:
    """Parses input file and returns list of groups"""
    groups: List[str] = []

    if not os.path.isfile(file):
        exit_with_error("File {} does not exist or is not a regular file.".format(file))
    with open(file, 'r') as input:
        for line in input:
            groups.append(line.strip())

    if len(groups) == 0:
        exit_with_error("File has no groups.")

    return groups


def get_data_objs_with_checksum(session: iRODSSession, grp: str, grp_coll: str) -> List[Dict[str, Any]]:
    """
    Returns data of all data objects with a checksum in a group

    Returns a lists of dicts containing:
    - 'group': group owner of parent collection
    - 'parent': parent collection
    - 'dataobj': name of data object
    - 'chksum': checksum of data object
    - 'size': size of data object
    """
    data_objs = []

    # Get all data objects in collection and its subcollections
    searchstring = f"{grp_coll}/%"
    generator_collection = (session.query(Collection.name, DataObject.name, DataObject.size, DataObject.checksum)
                            .filter(Collection.name == grp_coll)
                            .filter(DataObject.checksum != "")
                            .filter(DataObject.replica_status == "1")
                            .get_results()
                            )
    generator_subcollections = (session.query(Collection.name, DataObject.name, DataObject.size, DataObject.checksum)
                                .filter(Like(Collection.name, searchstring))
                                .filter(DataObject.checksum != "")
                                .filter(DataObject.replica_status == "1")
                                .get_results()
                                )
    all_data_objs = chain(generator_collection, generator_subcollections)

    for row in all_data_objs:
        data_obj: Dict[str, Any] = {
            'group': grp,
            'parent': row[Collection.name],
            'dataobj': row[DataObject.name],
            'chksum': row[DataObject.checksum],
            'size': row[DataObject.size]
        }

        data_objs.append(data_obj)

    return data_objs


def run_get_duplicates(session: iRODSSession, intake_grps: List[str], research_grps: List[str]) -> List[Dict[str, Any]]:
    """Retrieves a list of data objects for a list of research groups and intake groups, then
       calculates duplicates."""
    intake_dataobjs = []
    for grp in intake_grps:
        grp_coll = f"/{session.zone}/home/{grp}"
        if collection_exists(session, grp_coll):
            intake_dataobjs.extend(get_data_objs_with_checksum(session, grp, grp_coll))

    if len(intake_dataobjs) == 0:
        exit_with_error("No data objects found for any of the intake vault groups provided.")

    research_dataobjs = []
    for grp in research_grps:
        grp_coll = f"/{session.zone}/home/{grp}"
        if collection_exists(session, grp_coll):
            research_dataobjs.extend(get_data_objs_with_checksum(session, grp, grp_coll))

    if len(research_dataobjs) == 0:
        exit_with_error("No data objects found for any of the research groups provided.")

    return get_duplicates(research_dataobjs, intake_dataobjs)


def get_duplicates(research_dataobjs: List[Dict[str, Any]], intake_dataobjs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    intake_chksum_lookup = _get_dataobject_lookup_dict(intake_dataobjs, "chksum")
    intake_name_lookup = _get_dataobject_lookup_dict(intake_dataobjs, "dataobj")

    duplicates: List[Dict[str, Any]] = []
    for r_dataobj in research_dataobjs:
        checksum: str = r_dataobj['chksum']
        name: str = r_dataobj['dataobj']

        if checksum in intake_chksum_lookup and name in intake_name_lookup:
            intake_objects_by_name = intake_name_lookup[name]
            intake_objects_by_checksum  = intake_chksum_lookup[checksum]
            intake_objects_that_match: List[Dict[str, Any]] = [o for o in intake_objects_by_name if o in intake_objects_by_checksum]
            if len(intake_objects_that_match) > 0:
                match = r_dataobj.copy()
                match["duplicateOf"] = ",".join([o['parent'] + "/" + o['dataobj'] for o in intake_objects_that_match])
                duplicates.append(match)

    return duplicates


def _get_dataobject_lookup_dict(data: List[Dict[str, Any]], indexkey: str) -> Dict[str, List[Dict[str, Any]]]:
    """Creates a lookup dictionary for a list of dictionaries by a particular
       key."""
    output: Dict[str, List[Dict[str, Any]]] = {}

    for entry in data:
        k: str = entry[indexkey]
        if k in output:
            output[k].append(entry)
        else:
            output[k] = [entry]

    return output


def size_to_str(value: int, human_readable: bool) -> str:
    if value is None or value == '':
        return 'N/A'
    elif human_readable:
        return humanize.naturalsize(value, binary=True)
    else:
        return str(value)


def report_intake_duplication(args: argparse.Namespace, session: iRODSSession, intake_grps: List[str], research_grps: List[str]) -> None:
    """Generate duplication report between intake and research collections."""
    writer = csv.DictWriter(sys.stdout, fieldnames=['Group', 'Collection', 'Data object', 'Chksum', 'Size', 'Duplicate of'], delimiter=',')
    writer.writeheader()

    duplicates = run_get_duplicates(session, intake_grps, research_grps)
    total_size: int = 0
    for dup in duplicates:
        row = {
            'Group': dup['group'],
            'Collection': dup['parent'],
            'Data object': dup['dataobj'],
            'Chksum': dup['chksum'],
            'Size': size_to_str(dup['size'], args.human_readable),
            'Duplicate of': dup['duplicateOf']
        }

        total_size += int(dup['size'])

        try:
            writer.writerow(row)
        except Exception as e:
            print(f"Error writing row: {e}", file=sys.stderr)

    print(f"Total size of duplicates: {size_to_str(total_size, args.human_readable)}")


def exit_with_error(message: str):
    print("Error: {}".format(message), file=sys.stderr)
    sys.exit(1)
