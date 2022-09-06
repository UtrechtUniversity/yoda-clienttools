"""Removes a list of user accounts. This script needs to run locally on the environment."""

import argparse
import contextlib
import os
import re
import subprocess
import sys

from yclienttools import session as s
from yclienttools.common_queries import get_collections_in_root, get_collection_size
from yclienttools.common_rules import RuleInterface
from yclienttools.options import GroupByOption


def _get_args():
    '''Parse command line arguments'''

    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=_get_format_help_text(),
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('userfile', help='Name of the user file')
    parser.add_argument("-y", "--yoda-version", default ="1.7", choices = ["1.7", "1.8"],
                        help="Yoda version on the server (default: 1.7)")
    parser.add_argument('--check', '-c', action='store_true',
                             help='Check mode: verifies user exist and home directories are empty')
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
                             help='Verbose mode: print additional debug information.')
    parser.add_argument('--dry-run', '-d', action='store_true', default=False,
                             help="Dry run mode: show what action would be taken.")
    return parser.parse_args()


def _get_format_help_text():
    return 'The user file is a text file, with one user name on each line.'


def validate_data(session, rule_interface, args, userdata):
    errors = []

    for user in userdata:
        if not rule_interface.call_uuUserExists(user):
            errors.append(f"User {user} does not exist.")
        if home_exists(session, user) and not home_is_empty(session, user):
            errors.append(f"Home directory of user {user} is not empty")

    return errors


def remove_users(rule_interface, args, users, verbose, dry_run):
    for user in users:
        if verbose or dry_run:
            prefix = "Removing" if verbose else "Would remove"
            print(f"{prefix} user {user} ...")
        if not dry_run:
            p = subprocess.Popen(["iadmin", "rmuser", user])
            p.communicate()
            if ( p.returncode == 0 ):
                if verbose:
                    print(f"User {user} has been successfully removed")
            else:
                _print_error(f"Error code during removing user {user}: {str(p.returncode)}.")


def entry():
    '''Entry point'''
    args = _get_args()
    userdata = parse_user_file(args.userfile)

    session = s.setup_session(args,
        require_ssl = False if args.yoda_version == "1.7" else True)
    rule_interface = RuleInterface(session,
        set_re = False if args.yoda_version == "1.7" else True)

    try:
        validation_errors = validate_data(session, rule_interface, args, userdata)

        if len(validation_errors) > 0:
            _exit_with_validation_errors(validation_errors)

        if not args.check:
            remove_users(rule_interface, args, userdata, args.verbose, args.dry_run)

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)

    finally:
        session.cleanup()


def parse_user_file(userfile):
    users = []

    if not os.path.isfile(userfile):
        _exit_with_error("User file {} does not exist or is not a regular file.".format(userfile))

    with _open_file_or_stdin(userfile, "r") as input:
        for line in input:
            users.append(line.strip().lower())

    if len(users) == 0:
        _exit_with_error("User file has no users.")

    return users

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

def home_exists(session, user):
    home_collection = f"/{session.zone}/home/{user}"
    return len(list(get_collections_in_root(session, home_collection))) > 0


def home_is_empty(session, user):
    home_collection = f"/{session.zone}/home/{user}"
    num_collections = len(list(get_collections_in_root(session, home_collection)))
    num_objects = get_collection_size(session, home_collection, False, GroupByOption.none, False)['all']
    return num_collections <= 1 and num_objects == 0


def _print_error(message):
    print("Error: {}".format(message), file=sys.stderr)


def _exit_with_error(message):
    _print_error(message)
    sys.exit(1)


def _exit_with_validation_errors(errors):
    for error in errors:
        print("Validation error: {}".format(error), file=sys.stderr)
    sys.exit(1)
