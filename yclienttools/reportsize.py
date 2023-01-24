'''Shows a report of the size of all data objects in a (set of) collections'''

import argparse
import humanize
import csv
import sys
from irods.models import Collection, User, UserMeta
from yclienttools import session, exceptions
from yclienttools.common_queries import collection_exists, get_collection_size
from yclienttools.options import GroupByOption


def entry():
    '''Entry point'''
    try:
        args = _get_args()
        s = session.setup_session(args,
            require_ssl = False if args.yoda_version == "1.7" else True)

        report_size(args, s)
        s.cleanup()
    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)


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
    parser.add_argument("-y", "--yoda-version", default ="1.7", choices = ["1.7", "1.8","1.9"],
                        help="Yoda version on the server (default: 1.7)")
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

            size_result = get_collection_size(
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

        if collection_exists(session, research_collection):
            results.append(research_collection)

        if _username_refers_to_research_collection(user[User.name]):
            vault_collection = _get_vault_collection_for_username(
                session, user[User.name])

            if collection_exists(session, vault_collection):
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
