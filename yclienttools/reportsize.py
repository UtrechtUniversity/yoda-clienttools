'''Shows a report of the size of all data objects in a (set of) collections'''

import argparse
import csv
import sys
from irods.models import Collection, DataObject
from yclienttools import common_queries, session

def entry():
    '''Entry point'''
    report_size(_get_args(), session.setup_session())


def _get_args():
    '''Parse command line arguments'''
    # Add_help is False, because we the -h option would conflict with our custom -h option.
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('--help', action='help', help='show help information')
    subject_group = parser.add_mutually_exclusive_group(required=True)
    subject_group.add_argument("-c", "--collection",
                               help='Show total size of data objects in this collection and its subcollections')
    subject_group.add_argument("-h", "--all-collections-in-home", action='store_true',
                               help='Show total size of data objects in each collection in /zoneName/home, including its subcollections.')
    return parser.parse_args()


def _get_collection_size(session, collection_name):
    total_size = 0

    for collection in common_queries.get_collections_in_root(
            session, collection_name):
        dataobjects = (session.query(Collection.name, DataObject.name, DataObject.size)
                       .filter(Collection.name == collection[Collection.name])
                       .get_results())
        for dataobject in dataobjects:
            total_size = total_size + dataobject[DataObject.size]
    return total_size


def _report_size_collections(session, collections):
    output = csv.writer(sys.stdout, delimiter=',')
    for collection in collections:
        output.writerow([
            collection, str(
                _get_collection_size(
                    session, collection))])


def _get_all_collections_in_home(session):
    '''Returns a list of the names of all collection names in the home collection.'''
    home_collection = "/{}/home".format(session.zone)
    collections = (session.query(Collection.name)
            .filter(Collection.parent_name == home_collection)
            .get_results())
    return [ c[Collection.name] for c in collections ]


def report_size(args, session):
    if args.collection:
        _report_size_collections(session, [args.collection])
    elif args.all_collections_in_home:
        _report_size_collections(session,
                                 _get_all_collections_in_home(session))
