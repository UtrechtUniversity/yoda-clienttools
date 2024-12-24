'''Generates a list of direct subcollections of a deposit group collection, along with their
   size, owner, creation date and last modified date.

   The report can be used by data managers to determine which pending deposits might need to be
   cleaned up.

'''

import argparse
import csv
import datetime
import sys
from typing import List, Union

import humanize
from irods.message import (ET, XML_Parser_Type)
from irods.models import Collection
from irods.session import iRODSSession
from yclienttools import common_args, common_config, session as s
from yclienttools.common_queries import get_collection_contents_last_modified, get_collection_size
from yclienttools.options import GroupByOption


def entry():
    '''Entry point'''
    try:
        args = _get_args()
        yoda_version = args.yoda_version if args.yoda_version is not None else common_config.get_default_yoda_version()
        session = s.setup_session(yoda_version)
        if args.quasi_xml:
            ET(XML_Parser_Type.QUASI_XML, session.server_version)
        report_pending_deposits(args, session)
        session.cleanup()

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)


def _get_args() -> argparse.Namespace:
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", default="deposit-pilot", nargs='?',
                        help="deposit group to process (default: deposit-pilot)")
    parser.add_argument("-q", "--quasi-xml", default=False, action='store_true',
                        help='Enable Quasi-XML parser in order to be able to parse characters not supported by regular XML parser')
    parser.add_argument("-H", "--human-readable", default=False, action='store_true',
                        help='Report sizes in human-readable figures')
    common_args.add_default_args(parser)
    return parser.parse_args()


def _get_collection_size_for_pdr(session: iRODSSession, collection_name: str) -> int:
    return get_collection_size(session, collection_name, True, GroupByOption.none, False)['all']


def _get_collection_owner(session: iRODSSession, collection_name: str) -> str:
    create_times = list(session.query(
        Collection.owner_name).filter(
        Collection.name == collection_name).get_results())
    return create_times[0][Collection.owner_name]


def _get_collection_creation_date(session: iRODSSession, collection_name: str) -> datetime.datetime:
    create_times = list(session.query(
        Collection.create_time).filter(
        Collection.name == collection_name).get_results())
    return create_times[0][Collection.create_time]


def _get_direct_subcollections(session: iRODSSession, parent_collection_name: str) -> List[str]:
    subcollections = list(session.query(
        Collection.name).filter(
        Collection.parent_name == parent_collection_name).get_results())
    return [subcollection[Collection.name] for subcollection in subcollections]


def _get_columns() -> List[str]:
    return ["Collection name", "Creation date", "Last modification date", "Creator", "Size"]


def _size_to_str(value: Union[int, None], human_readable: bool) -> str:
    if value is None:
        return "N/A"
    elif human_readable:
        return humanize.naturalsize(value, binary=True)
    else:
        return str(value)


def get_deposit_collection(session: iRODSSession, group_name: str) -> str:
    return f"/{session.zone}/home/{group_name}"


def _timestamp_to_date_str(value: Union[datetime.datetime, None]) -> str:
    return "N/A" if value is None else value.strftime("%Y-%m-%d")


def report_pending_deposits(args: argparse.Namespace, session: iRODSSession):
    output = csv.writer(sys.stdout, delimiter=',')
    output.writerow(_get_columns())
    group_collection = get_deposit_collection(session, args.group)

    for collection in _get_direct_subcollections(session, group_collection):
        owner_name = _get_collection_owner(session, collection)
        creation_date = _get_collection_creation_date(session, collection)
        size = _get_collection_size_for_pdr(session, collection)
        last_modified_date = get_collection_contents_last_modified(session, collection)
        rowdata = [collection,
                   creation_date.strftime("%Y-%m-%d"),
                   last_modified_date.strftime("%Y-%m-%d") if last_modified_date is not None else "N/A",
                   owner_name,
                   _size_to_str(size, args.human_readable)]

        output.writerow(rowdata)
