'''Shows a report of the size of all data objects in a (set of) collections'''

import argparse
from enum import Enum
import humanize
import itertools
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
    try:
        s = session.setup_session()
        report_size(_get_args(), s)
        s.cleanup()
    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file = sys.stderr)


def exit_with_error(session, message):
    '''Closes iRODS API session, and exits with an error message.'''
    session.cleanup()
    print(message, file=sys.stderr)
    sys.exit(1)


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
    parser.add_argument("-R", '--include-revisions', action='store_true', default=False,
                        help="Include the size of stored revisions of data objects in the collection (if available).")
    parser.add_argument("-g", "--group-by", type=GroupByOption, default='none',
                        help="Group collection sizes by resource or by location. Argument should be 'none' (the default), " +
                             "'resource' or 'location'. Grouping by resource or location implies --count-all-replicas. " +
                             "If a collection has no dataobjects and --group-by resource / location is enabled, its size " +
                             "will be printed with group 'all'.")
    subject_group = parser.add_mutually_exclusive_group(required=True)
    subject_group.add_argument("-c", "--collection",
                               help='Show total size of data objects in this collection and its subcollections')
    subject_group.add_argument("-H", "--all-collections-in-home", action='store_true',
                               help='Show total size of data objects in each collection in /zoneName/home, including its subcollections. ' +
                               "Note: you will only see the collections you have access to.")
    subject_group.add_argument("-C", "--community",
                               help='Show total size of data objects in each research and vault collection in a Yoda community. ' +
                               "Note: you will only see the collections you have access to.")

    args = parser.parse_args()

    if args.group_by != GroupByOption.none and not args.count_all_replicas:
        print(
            "Automatically enabled --count-all-replicas, because --group-by resource or location is enabled.",
            file=sys.stderr)
        args.r = True
        args.count_all_replicas = True

    return args


def _get_revision_collection_name(session, collection_name):
    '''Returns the revision collection name of a collection if it exists, otherwise None. '''
    expected_prefix = "/{}/home/".format(session.zone)
    if collection_name.startswith(expected_prefix):
        trimmed_collection_name = collection_name.replace(
            expected_prefix, "", 1)
        if "/" in trimmed_collection_name:
            return None
        else:
            revision_collection_name = "/{}/yoda/revisions/{}".format(
                session.zone, trimmed_collection_name)
            if _collection_exists(session, revision_collection_name):
                return revision_collection_name
            else:
                return None
    else:
        return None


def _get_collection_size(session, collection_name,
                         count_all_replicas, group_by, include_revisions):
    result = {}

    collections = common_queries.get_collections_in_root(
        session, collection_name)

    if len(list(collections)) == 0:
        raise exceptions.NotFoundException

    original_collections = common_queries.get_collections_in_root(
        session, collection_name)
    revision_collection_name = _get_revision_collection_name(
        session, collection_name)

    if revision_collection_name is None or not include_revisions:
        all_collections = original_collections
    else:
        revision_collections = common_queries.get_collections_in_root(
            session, revision_collection_name)
        all_collections = itertools.chain(
            original_collections, revision_collections)

    for collection in all_collections:
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


def _print_entry(csv_output, collection, group,
                 raw_size, group_by, human_readable):
    '''Prints an entry of the collection size report.'''

    if human_readable:
        display_size = str(humanize.naturalsize(raw_size))
    else:
        display_size = str(raw_size)

    if group_by == GroupByOption.none:
        csv_output.writerow([collection, display_size])
    else:
        csv_output.writerow([collection, group, display_size])


def _report_size_collections(
        session, human_readable, count_all_replicas, group_by, include_revisions, collections):
    '''Prints a list of collections, along with the total size of their data objects,
       including any data objects in subcollections.'''
    output = csv.writer(sys.stdout, delimiter=',')
    totals = {}
    for collection in collections:
        try:

            size_result = _get_collection_size(
                session, collection, count_all_replicas, group_by, include_revisions,)

            for group, raw_size in size_result.items():
                _print_entry(
                    output,
                    collection,
                    group,
                    raw_size,
                    group_by,
                    human_readable)

                if group in totals:
                    totals[group] = totals[group] + raw_size
                else:
                    totals[group] = raw_size

        except exceptions.NotFoundException:
            exit_with_error(session, "Error: collection {} not found (or access denied).".format(
                collection))

    if len(list(collections)) > 1:
        # Print total size per group if the output is about multiple
        # collections.
        if len(totals.items()) > 1:
            totals.pop('all', None)

        for group, raw_size in totals.items():
            _print_entry(
                output,
                'total',
                group,
                raw_size,
                group_by,
                human_readable)


def _get_all_collections_in_home(session):
    '''Returns a list of the names of all collection names in the home collection.'''
    home_collection = "/{}/home".format(session.zone)
    collections = (session.query(Collection.name)
                   .filter(Collection.parent_name == home_collection)
                   .get_results())
    return [c[Collection.name] for c in collections]


def _collection_exists(session, collection):
    '''Returns a boolean value that indicates whether a collection with the provided name exists.'''
    return len(list(session.query(Collection.name).filter(
        Collection.name == collection).get_results())) > 0


def _get_research_collection_for_username(session, name):
    '''Returns the research collection name for a user name, e.g. research-foo ->
    /zoneName/home/research-foo. '''
    return "/{}/home/{}".format(session.zone, name)


def _get_vault_collection_for_username(session, name):
    '''Returns the vault collection name for a user name, e.g. research-foo ->
    /zoneName/home/vault-foo. '''
    return "/{}/home/{}".format(session.zone,
                                name.replace("research-", "vault-", 1))


def _username_refers_to_research_collection(name):
    '''Returns boolean value that says whether a user name appears to refer a research collection. '''
    return name.startswith("research-")


def _get_all_root_collections_in_community(session, community):
    '''Returns a list of all root collections in a Yoda community/category.'''
    results = []
    # Community information is stored by Yoda in user objects. So first search
    # for user objects, and get the collection names from there.
    for user in session.query(User.name, UserMeta).filter(
            UserMeta.name == 'category', UserMeta.value == community).get_results():

        research_collection = _get_research_collection_for_username(
            session, user[User.name])

        if _collection_exists(session, research_collection):
            results.append(research_collection)

        if _username_refers_to_research_collection(user[User.name]):
            vault_collection = _get_vault_collection_for_username(
                session, user[User.name])

            if _collection_exists(session, vault_collection):
                results.append(vault_collection)

    if len(results) == 0:
        raise exceptions.NotFoundException

    return results


def report_size(args, session):
    if args.collection:
        _report_size_collections(
            session, args.human_readable, args.count_all_replicas, args.group_by, args.include_revisions, [
                args.collection])
    elif args.all_collections_in_home:
        _report_size_collections(session, args.human_readable, args.count_all_replicas, args.group_by, args.include_revisions,
                                 _get_all_collections_in_home(session))
    elif args.community:
        try:
            collections = _get_all_root_collections_in_community(session,
                                                                 args.community)
        except exceptions.NotFoundException:
            exit_with_error(session, "Error: community {} not found.".format(
                args.community))

        _report_size_collections(
            session,
            args.human_readable,
            args.count_all_replicas,
            args.group_by,
            args.include_revisions,
            collections)
