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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-c", "--collection", required=True,
                        help='Show total size of data objects in this collection and its subcollections')
    return parser.parse_args()


def _get_collection_size(session, collection_name):
    total_size = 0
    all_collections = session.query(
        Collection.id, Collection.name).get_results()

    for collection in common_queries.get_collections_in_root(
            session, collection_name):
        dataobjects = (session.query(Collection.name, DataObject.name, DataObject.size)
                       .filter(Collection.name == collection[Collection.name])
                       .get_results())
        for dataobject in dataobjects:
            total_size = total_size + dataobject[DataObject.size]
    return total_size


def report_size(args, session):
    output = csv.writer(sys.stdout, delimiter=',')
    output.writerow([
        args.collection, str(
            _get_collection_size(
                session, args.collection))])
