'''Shows a report of the size of all data objects in a (set of) collections'''

import argparse
from enum import Enum
import humanize
import csv
import sys
from irods.models import Collection, DataObject, Resource, User, UserMeta
from yclienttools import common_queries, session, exceptions


class GroupByOption(Enum):
    none = 'none'
    resource = 'resource'
    location = 'location'

    def __str__(self):
        return self.name


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
    parser.add_argument("-r", '--count-all-replicas', action='store_true', default=False,
                        help="Count the size of all replicas of a data object. By default, only " +
                        "the size of one replica of each data object is counted.")
    parser.add_argument("-g", "--group-by", type=GroupByOption, default='none',
                        help="Group collection sizes by resource or by location. Argument should be 'none' (the default), " +
                             "'resource' or 'location'. Grouping by resource or location implies --count-all-replicas. " +
                             "If a collection has no dataobjects and --group-by resource / location is enabled, its size " +
                             "will be printed with group 'all'.")
    subject_group = parser.add_mutually_exclusive_group(required=True)
    subject_group.add_argument("-c", "--collection",
                               help='Show total size of data objects in this collection and its subcollections')
    subject_group.add_argument("-H", "--all-collections-in-home", action='store_true',
                               help='Show total size of data objects in each collection in /zoneName/home, including its subcollections.')
    subject_group.add_argument("-C", "--community",
                               help='Show total size of data objects in each research and vault collection in a Yoda community')

    args = parser.parse_args()

    if args.group_by != GroupByOption.none and not args.count_all_replicas:
        print(
            "Automatically enabled --count-all-replicas, because --group-by resource or location is enabled.",
            file=sys.stderr)
        args.r = True
        args.count_all_replicas = True

    return args


def _get_collection_size(session, collection_name,
                         count_all_replicas, group_by):
    result = {}

    collections = common_queries.get_collections_in_root(
        session, collection_name)

    if len(list(collections)) == 0:
        raise exceptions.NotFoundException

    for collection in common_queries.get_collections_in_root(
            session, collection_name):
        if count_all_replicas:
            dataobjects = (session.query(Collection.name, DataObject.name, DataObject.size,
                                         DataObject.path, Resource.name, Resource.location)
                           .filter(Collection.name == collection[Collection.name])
                           .get_results())
        else:
            dataobjects = (session.query(Collection.name, DataObject.name, DataObject.size)
                           .filter(Collection.name == collection[Collection.name])
                           .get_results())
        for dataobject in dataobjects:

            if group_by == GroupByOption.none:
                key = 'all'
            elif group_by == GroupByOption.resource:
                key = dataobject[Resource.name]
            elif group_by == GroupByOption.location:
                key = dataobject[Resource.location]
            else:
                raise Exception("Unknown group_by value {}".format(key))

            if key in result:
                result[key] = result[key] + dataobject[DataObject.size]
            else:
                result[key] = dataobject[DataObject.size]

    if len(result.keys()) == 0:
        result['all'] = 0

    return result


def _report_size_collections(
        session, human_readable, count_all_replicas, group_by, collections):
    '''Prints a list of collections, along with the total size of their data objects,
       including any data objects in subcollections.'''
    output = csv.writer(sys.stdout, delimiter=',')
    for collection in collections:
        try:

            size_result = _get_collection_size(
                session, collection, count_all_replicas, group_by)

            for group, raw_size in size_result.items():

                if human_readable:
                    display_size = str(humanize.naturalsize(raw_size))
                else:
                    display_size = str(raw_size)

                if group_by == GroupByOption.none:
                    output.writerow([collection, display_size])
                else:
                    output.writerow([collection, group, display_size])

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
    for user in session.query(User.name, UserMeta).filter(
            UserMeta.name == 'category', UserMeta.value == community).get_results():

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
            session, args.human_readable, args.count_all_replicas, args.group_by, [
                args.collection])
    elif args.all_collections_in_home:
        _report_size_collections(session, args.human_readable, args.count_all_replicas, args.group_by,
                                 _get_all_collections_in_home(session))
    elif args.community:
        try:
            collections = _get_all_root_collections_in_community(session,
                                                                 args.community)
        except exceptions.NotFoundException:
            print(
                "Error: community {} not found.".format(
                    args.community),
                file=sys.stderr)
            sys.exit(1)

        _report_size_collections(
            session,
            args.human_readable,
            args.count_all_replicas,
            args.group_by,
            collections)
