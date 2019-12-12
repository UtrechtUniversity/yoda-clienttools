'''Shows a report of the size of all data objects in a (set of) collections'''

import argparse
import humanize
import csv
import sys
from irods.models import Collection, DataObject, User
from yclienttools import common_queries, session, exceptions


def entry():
    '''Entry point'''
    report_size(_get_args(), session.setup_session())


def _get_args():
    '''Parse command line arguments'''
    # Add_help is False, because we the -h option would conflict with our
    # custom -h option.
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('--help', action='help', help='show help information')
    parser.add_argument('-h', '--human-readable', action='store_true', default=False,
                        help="Show sizes in human readable format, e.g. 1.0MB instead of 1000000")
    subject_group = parser.add_mutually_exclusive_group(required=True)
    subject_group.add_argument("-c", "--collection",
                               help='Show total size of data objects in this collection and its subcollections')
    subject_group.add_argument("-H", "--all-collections-in-home", action='store_true',
                               help='Show total size of data objects in each collection in /zoneName/home, including its subcollections.')
    subject_group.add_argument("-C", "--all-collections-in-community",
                               help='Show total size of data objects in each research and vault collection in a Yoda community')
    return parser.parse_args()


def _get_collection_size(session, collection_name):
    total_size = 0

    collections = common_queries.get_collections_in_root(
        session, collection_name)

    if len(list(collections)) == 0:
        raise exceptions.NotFoundException

    for collection in common_queries.get_collections_in_root(
            session, collection_name):
        dataobjects = (session.query(Collection.name, DataObject.name, DataObject.size)
                       .filter(Collection.name == collection[Collection.name])
                       .get_results())
        for dataobject in dataobjects:
            total_size = total_size + dataobject[DataObject.size]
    return total_size


def _report_size_collections(session, human_readable, collections):
    '''Prints a list of collections, along with the total size of their data objects,
       including any data objects in subcollections.'''
    output = csv.writer(sys.stdout, delimiter=',')
    for collection in collections:
        try:

            size = _get_collection_size(session, collection)

            if human_readable:
                display_size = str(humanize.naturalsize(size))
            else:
                display_size = str(size)

            output.writerow([collection, display_size])

        except exceptions.NotFoundException:
            print("Error: collection {} not found.".format(
                collection), file=sys.stderr)


def _get_all_collections_in_home(session):
    '''Returns a list of the names of all collection names in the home collection.'''
    home_collection = "/{}/home".format(session.zone)
    collections = (session.query(Collection.name)
                   .filter(Collection.parent_name == home_collection)
                   .get_results())
    return [c[Collection.name] for c in collections]


def _get_all_root_collections_in_community(session, community):
    '''Returns a list of all root collections in a Yoda community/category.'''
    results = []
    # Community information is stored by Yoda in user objects. So first search
    # for user objects, and get the collection names from there.
    for user in session.query(User.name).get_results():
        metadata = session.metadata.get(User, user[User.name])
        categories = [m.value for m in metadata if m.name == 'category']

        if community in categories:

            research_collection = "/{}/home/{}".format(
                session.zone, user[User.name])
            results.append(research_collection)

            if user[User.name].startswith("research-"):
                vault_collection = "/{}/home/{}".format(
                    session.zone, user[User.name].replace("research-", "vault-", 1))

                if len(list(session.query(Collection.name).filter(
                        Collection.name == vault_collection).get_results())) > 0:
                    # If a matching vault collection exists, add it to the
                    # list as well.
                    results.append(vault_collection)

    if len(results) == 0:
        raise exceptions.NotFoundException

    return results


def report_size(args, session):
    if args.collection:
        _report_size_collections(
            session, args.human_readable, [
                args.collection])
    elif args.all_collections_in_home:
        _report_size_collections(session, args.human_readable,
                                 _get_all_collections_in_home(session))
    elif args.all_collections_in_community:
        try:
            collections = _get_all_root_collections_in_community(session,
                                                                 args.all_collections_in_community)
        except exceptions.NotFoundException:
            print(
                "Error: community {} not found.".format(
                    args.all_collections_in_community),
                file=sys.stderr)
            sys.exit(1)

        _report_size_collections(session, args.human_readable, collections)
