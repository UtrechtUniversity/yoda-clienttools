'''Shows a report of number of data objects and subcollections per collection'''

import argparse
import csv
import sys
from itertools import chain
from irods.column import Like
from irods.models import Collection, DataObject
from yclienttools import common_queries, session

def entry():
    '''Entry point'''
    report_collections(_get_args().root, session.setup_session())


def _get_args():
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-r", "--root", default="/",
                        help='show only collections in this root collection (default: show all collections')
    return parser.parse_args()


def _get_subcollections(session, collection_name):
    '''Get a nonrecursive list of child collections of a collection'''
    return (session.query(Collection.id, Collection.name)
            .filter(Collection.parent_name == collection_name)
            .get_results())


def _get_dataobjects_in_collection(session, collection_name):
    '''Get a nonrecursive list of data objects in a collection'''
    return (session.query(Collection.name, DataObject.name)
            .filter(Collection.name == collection_name)
            .get_results())


def report_collections(root, session):
    '''Print list of number of subcollections and data objects per collection'''
    output = csv.writer(sys.stdout, delimiter=',')
    for collection in common_queries.get_collections_in_root(session, root):
        collection_name = collection[Collection.name]
        num_collections = len(
            list(
                _get_subcollections(
                    session,
                    collection_name)))
        num_dataobjects = len(set(
            map(lambda d: d[DataObject.name],
                _get_dataobjects_in_collection(session, collection_name))))
        output.writerow([
            str(num_collections),
            str(num_dataobjects),
            str(num_collections + num_dataobjects),
            collection_name ])
