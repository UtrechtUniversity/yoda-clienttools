'''Shows a report of number of data objects and subcollections per collection'''

import argparse
import csv
import sys
from irods.models import Collection, DataObject
from yclienttools import common_queries
from yclienttools import session as s


def entry():
    '''Entry point'''
    try:
        session = s.setup_session()
        args = _get_args()

        if args.root and not common_queries.collection_exists(session, args.root):
            print ("Error: collection {} does not exist (or you don't have access)".format(args.root),
                    file=sys.stderr)
            sys.exit(1)

        report_collections(args, session)
        session.cleanup()

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)


def _get_args():
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-r", "--root", default="/",
                        help='show only collections in this root collection (default: show all collections')
    parser.add_argument("-e", "--by-extension", default=False, action='store_true',
                        help='show number of data objects by extension for each collection')
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


def _get_extension(filename):
    '''Returns extension of a filename, or None if it doesn't have one'''
    if "." in filename:
        return filename.split(".")[-1]
    else:
        return None


def _filter_by_extension(filenames, extension):
    '''Filter list of filenames based on whether they have a particular extension (None: no extension).'''
    if extension is None:
        return [n for n in filenames if not "." in n]
    else:
        return [n for n in filenames if n.endswith("." + extension)]


def _write_regular(session, output, collection_name):
    '''Write CSV statistics using regular output (number of data objects and
       subcollections per collection)'''
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
        collection_name])


def _write_by_extension(session, output, collection_name):
    '''Write CSV statistics with number of subcollections and number of data
       objects by extension.'''
    num_collections = len(
        list(
            _get_subcollections(
                session,
                collection_name)))
    dataobject_names = list(map(lambda d: d[DataObject.name],
                                _get_dataobjects_in_collection(session, collection_name)))
    extensions = list(set(map(lambda n: _get_extension(n), dataobject_names)))
    if len(extensions) == 0:
        output.writerow([
            str(num_collections),
            "0",
            str(num_collections),
            "N/A",
            collection_name])
    else:
        for extension in extensions:
            num_dataobjects = len(
                _filter_by_extension(
                    list(dataobject_names),
                    extension))
            if (extension is None):
                extension_name = "No extension"
            else:
                extension_name = extension
            output.writerow([
                str(num_collections),
                str(num_dataobjects),
                str(num_collections + num_dataobjects),
                extension_name,
                collection_name])


def report_collections(args, session):
    '''Print list of number of subcollections and data objects per collection'''
    output = csv.writer(sys.stdout, delimiter=',')
    for collection in common_queries.get_collections_in_root(
            session, args.root):
        collection_name = collection[Collection.name]
        if args.by_extension:
            _write_by_extension(session, output, collection_name)
        else:
            _write_regular(session, output, collection_name)
