'''Recursively finds data objects in a collection that will typically have to be cleaned up when a dataset is archived, and deletes them. '''

import argparse
import csv
import os
import sys
from irods.column import Like
from irods.models import Collection, DataObject
from yclienttools import common_queries
from yclienttools import session as s


def entry():
    '''Entry point'''
    try:
        args = _get_args()
        session = s.setup_session(args,
            require_ssl = False if args.yoda_version == "1.7" else True)

        if not common_queries.collection_exists(session, args.root):
            print ("Error: collection {} does not exist (or you don't have access)".format(args.root),
                    file=sys.stderr)
            session.cleanup()
            sys.exit(1)

        objects_todelete = get_objects_to_delete(session, args.root)
        objects_todelete.sort()

        if len(objects_todelete) == 0:
            print("No objects to remove have been found.\n")
            session.cleanup()
            sys.exit(0)
        else:
            print("The following data objects have been found:\n\n")
            for dataobject in objects_todelete:
                print(" - {}".format(dataobject))
            print()
            ask_continue(session)

        delete_dataobjects(session, objects_todelete)

        session.cleanup()

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)

def _get_args():
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-r", "--root", default="/", required=True,
                        help='Delete unwanted files in this collection, as well as its subcollections')
    parser.add_argument("-y", "--yoda-version", default ="1.7", choices = ["1.7", "1.8", "1.9"],
                        help="Yoda version on the server (default: 1.7)")
    return parser.parse_args()

def _wildcard_to_like_query(name):
    '''Convert Unix-style filename with wildcard, such as *.csv, to a wildcard that is suitable for iRODS queries, like %.csv'''
    return name.replace('%','\\%').replace('_','\\_').replace('?','_').replace('*','%')

def _get_unwanted_files():
    return [ '._*',          # MacOS resource fork
             '.DS_Store',    # MacOS custom folder attributes
             'Thumbs.db'     # Windows thumbnail images
           ]

def _is_wildcard(name):
    return "?" in name or "*" in name

def get_objects_to_delete(session, root):
    '''Returns a list of objects that are candidates to be deleted.'''
    dataobjects = []

    for name in _get_unwanted_files():
        if _is_wildcard(name):
            dataobjects.extend( session.query(Collection.name, DataObject.name).filter(
                Collection.name == root).filter(
                Like(DataObject.name, _wildcard_to_like_query(name))).get_results())
            dataobjects.extend( session.query(Collection.name, DataObject.name).filter(
                Like(Collection.name, "{}/%".format(root))).filter(
                Like(DataObject.name, _wildcard_to_like_query(name))).get_results())
        else:
            dataobjects.extend( session.query(Collection.name, DataObject.name).filter(
                Collection.name == root).filter(
                DataObject.name == name).get_results())
            dataobjects.extend( session.query(Collection.name, DataObject.name).filter(
                Like(Collection.name, "{}/%".format(root))).filter(
                DataObject.name == name).get_results())

    return list(map (lambda n : "{}/{}".format(n[Collection.name],n[DataObject.name]), dataobjects))

def delete_dataobjects(session, dataobjects):
    '''Delete a list of dataobjects'''
    for dataobject in dataobjects:
        print("Deleting data object {}".format(dataobject))
        obj=session.data_objects.get(dataobject)
        obj.unlink(force=True)

def ask_continue(session):
    answer = input("Do you want to delete these data objects (yes/no)? ")
    if not answer.lower().rstrip() in ['y','yes']:
        session.cleanup()
        sys.exit(0)
