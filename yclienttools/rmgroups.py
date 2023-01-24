"""Removes a list of (research) groups"""

import argparse
import contextlib
import os
import re
import subprocess
import sys

from yclienttools import session as s
from yclienttools.common_file_ops import remove_collection_data
from yclienttools.common_queries import get_collections_in_root, get_collection_size
from yclienttools.common_rules import RuleInterface
from yclienttools.options import GroupByOption


def _get_args():
    '''Parse command line arguments'''

    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=_get_format_help_text(),
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('groupfile', help='Name of the group file')
    parser.add_argument("-y", "--yoda-version", default ="1.7", choices = ["1.7", "1.8","1.9"],
                        help="Yoda version on the server (default: 1.7)")
    parser.add_argument("--remove-data", "-r", action='store_true',
                        help="Remove any data from the group, if needed.")
    parser.add_argument('--check', '-c', action='store_true',
                             help='Check mode: verifies groups exist, and checks if they are empty')
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
                             help='Verbose mode: print additional debug information.')
    parser.add_argument('--dry-run', '-d', action='store_true', default=False,
                             help="Dry run mode: show what action would be taken.")
    parser.add_argument('--continue-failure', '-C', action='store_true', default=False,
                             help="Continue if operations to remove collections or data objects return an error code")
    return parser.parse_args()


def _get_format_help_text():
    return 'The group file is a text file, with one group name (e.g.: research-foo) on each line'


def entry():
    '''Entry point'''
    args = _get_args()
    groupdata = parse_group_file(args.groupfile)

    session = s.setup_session(args,
        require_ssl = False if args.yoda_version == "1.7" else True)
    rule_interface = RuleInterface(session,
        set_re = False if args.yoda_version == "1.7" else True)

    try:
        validation_errors = validate_data(session, rule_interface, args, groupdata)

        if len(validation_errors) > 0:
            _exit_with_validation_errors(validation_errors)

        if not args.check:
            remove_groups(session, rule_interface, args, groupdata)

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)

    finally:
        session.cleanup()

def validate_data(session, rule_interface, args, groupdata):
    errors = []

    for group in groupdata:
        if args.verbose:
            print(f"Validating group {group} ...")
        if not rule_interface.call_uuGroupExists(group):
            errors.append(f"Group {group} does not exist.")
        elif not group_collection_exists(session, group):
            errors.append(f"Group collection {group} does not exist")
        elif not (args.remove_data or group_is_empty(session, group)):
            message = f"Group {group} is not empty. Need to use --remove-data to remove its contents."
            errors.append(message)

    return errors


def remove_groups(session, rule_interface, args, groups):
    for group in groups:

        # Safety checks
        if group == "":
            _exit_with_error(f"Cannot process empty group name")
        elif "/" in group or ".." in group:
            _exit_with_error(f"Refusing to process group name containing slash or dot dot, for safety reasons.")

        if args.verbose:
            print(f"Processing group {group} ...")
            print(f"Verifying whether group {group} is empty ...")

        group_empty = group_is_empty(session, group)
        if args.verbose:
            print(f"Group {group} is " + ( "empty" if group_empty else "not empty") )

        if not group_empty:
            group_coll = f"/{session.zone}/home/{group}"

            if args.dry_run:
                print(f"Would remove data from {group_coll} ...")
            elif args.verbose and not args.dry_run:
                print(f"Removing data from {group_coll} ...")

            remove_group_contents(session,
                                  rule_interface,
                                  group,
                                  args.verbose,
                                  args.dry_run,
                                  args.continue_failure)

        if args.dry_run:
            print(f"Would remove group {group} ...")
        else:
            if args.verbose:
                print(f"Removing group {group} ...")
            (status, err) = rule_interface.call_uuGroupRemove(group)
            if status != '0':
               message = f"Could not remove group {group}. Error: {err} (code {status})"
               if args.continue_failure:
                   _print_error(message)
               else:
                   _exit_with_error(message)


def remove_group_contents(session, rule_interface, group, verbose, dry_run, continue_failure):
    group_coll = f"/{session.zone}/home/{group}"
    rods_role = rule_interface.call_uuGroupGetMemberType(group, "rods")
    if rods_role == "none":
        if dry_run:
            print(f"Would add rods user to group {group} in order to remove data")
        else:
            if verbose:
                print(f"Adding rods user to group {group} in order to remove data ...")
            rule_interface.call_uuGroupUserAdd(group, "rods")
    if rods_role != "manager":
        if dry_run:
            print (f"Would make rods user manager of group {group} in order to remove data")
        else:
            if verbose:
                print(f"Making rods user manager of group {group} in order to remove data ...")
            rule_interface.call_uuGroupUserChangeRole(group, "rods", "manager")
    if verbose:
        print(f"Removing data from group {group_coll} (dry run mode: { str(dry_run) } ...")
    remove_collection_data(group_coll, verbose, dry_run, continue_failure, False)


def group_collection_exists(session, group):
    group_collection = f"/{session.zone}/home/{group}"
    return len(list(get_collections_in_root(session, group_collection))) > 0


def group_is_empty(session, group):
    group_collection = f"/{session.zone}/home/{group}"
    num_collections = len(list(get_collections_in_root(session, group_collection)))
    num_objects = get_collection_size(session, group_collection, False, GroupByOption.none, False)['all']
    return num_collections <= 1 and num_objects == 0


def parse_group_file(groupfile):
    groups = []

    if not os.path.isfile(groupfile):
        _exit_with_error("Group file {} does not exist or is not a regular file.".format(groupfile))

    with _open_file_or_stdin(groupfile, "r") as input:
        for line in input:
            group = line.strip().lower()
            if group != "":
                groups.append(group)

    if len(groups) == 0:
        _exit_with_error("Group file has no groups.")

    return groups


@contextlib.contextmanager
def _open_file_or_stdin(filename, mode):
    if filename == '-':
        f = sys.stdin
    elif not os.path.isfile(filename):
        _exit_with_error("File {} does not exist or is not a regular file.".format(filename))
    else:
        f = open(filename, mode)

    try:
        yield f
    finally:
        if filename != '-':
            f.close()


def _print_error(message):
    print("Error: {}".format(message), file=sys.stderr)


def _exit_with_error(message):
    _print_error(message)
    sys.exit(1)


def _exit_with_validation_errors(errors):
    for error in errors:
        print("Validation error: {}".format(error), file=sys.stderr)
    sys.exit(1)
