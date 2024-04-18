"""Ensures each research group in a list has a common set of members with a particular role. For example:
   one user has a manager role in all groups."""

import argparse
import contextlib
import os
import re
import sys

from yclienttools import common_args, common_config
from yclienttools import session as s
from yclienttools.common_rules import RuleInterface


def _get_args():
    '''Parse command line arguments'''

    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=_get_format_help_text(),
        formatter_class=argparse.RawTextHelpFormatter)
    common_args.add_default_args(parser)
    parser.add_argument('userfile', help='Name of the user file')
    parser.add_argument('groupfile', help='Name of the group file ("-" for standard input)')
    parser.add_argument('-i', '--internal-domains', required=True,
                        help='Comma-separated list of internal email domains to the Yoda server')
    actiongroup = parser.add_mutually_exclusive_group()
    actiongroup.add_argument('--offline-check', '-c', action='store_true',
                             help='Only checks user file format')
    actiongroup.add_argument('--online-check', '-C', action='store_true',
                             help='Check mode (online): Verifies that all users in the user file exist.')
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
                        help='Verbose mode: print additional debug information.')
    parser.add_argument('--dry-run', '-d', action='store_true', default=False,
                        help="Dry run mode: show what action would be taken.")
    return parser.parse_args()


def _get_format_help_text():
    return '''
        The user file is a text file. Each line has a role and an existing user account name,
        separated by ':':

        Roles are:

        'manager:'    = user that will be given the role of manager
        'member:'     = user that will be given the role of member with read/write
        'viewer:'     = user that will be given the role of viewer with read

        Example lines:
        manager:m.manager@uu.nl
        viewer:v.viewer@uu.nl

        The group file should have one group name on each line.
    '''


def validate_data(rule_interface, args, userdata, groupdata):
    errors = []

    for user in userdata:
        if not is_internal_user(user, args.internal_domains.split(",")):
            if not rule_interface.call_uuUserExists(user):
                errors.append("External user {} does not exist.".format(user))

    for group in groupdata:
        if not rule_interface.call_uuGroupExists(group):
            errors.append("Group {} does not exist.".format(group))

    return errors


def is_internal_user(username, internal_domains):
    for domain in internal_domains:
        domain_pattern = '@{}$'.format(domain)
        if re.search(domain_pattern, username) is not None:
            return True

    return False


def apply_data(rule_interface, args, userdata, groupdata, verbose, dry_run):
    for group in groupdata:
        apply_data_to_group(rule_interface, args, userdata, group, verbose, dry_run)


def apply_data_to_group(rule_interface, args, userdata, group, verbose, dry_run):

    if verbose or dry_run:
        print("Checking group {} ...".format(group))

    for user in sorted(userdata):
        role = userdata[user]
        if verbose or dry_run:
            print(" Checking user {} ...".format(user))

        current_role = rule_interface.call_uuGroupGetMemberType(group, user)

        # If user is not in group yet, add him/her
        if current_role == "none":
            if verbose and not dry_run:
                print("Adding user {} to group {} ...".format(user, group))

            if dry_run:
                print("Would add user {} to group {} ...".format(user, group))
            else:
                [status, msg] = rule_interface.call_uuGroupUserAdd(group, user)

                if status == "0":
                    current_role = "member"
                else:
                    print("Failed to add user {} to group {} ({}).".format(user, group, msg))

        # Adjust user role, if needed
        if _are_roles_equivalent(role, current_role):
            if verbose:
                print("Role user {} for group {} is already {} (okay)".format(user, group, role))
        else:
            if verbose and not dry_run:
                print("Changing role of user {} for group {} to {} ...".format(user, group, role))

            if dry_run:
                print("Would change role of user {} for group {} from {} to {}".format(user, group, current_role, role))
            else:
                [status, msg] = rule_interface.call_uuGroupUserChangeRole(group, user, _to_yoda_role_name(role))
                if status != "0":
                    _exit_with_error("Failed to change role of user {} for group: {} ({})".format(user, group, msg))


def _to_yoda_role_name(role):
    mapping = {"viewer": "reader",
               "member": "normal",
               "manager": "manager"}

    if role in mapping:
        return mapping[role]
    else:
        _exit_with_error("Cannot map role {} to Yoda role.".format(role))


def _are_roles_equivalent(a, b):
    """Checks whether two roles are equivalent. Needed because Yoda and Yoda-clienttools
       use slightly different names for the roles."""
    r_role_names = ["viewer", "reader"]
    m_role_names = ["member", "normal"]

    if a == b:
        return True
    elif a in r_role_names and b in r_role_names:
        return True
    elif a in m_role_names and b in m_role_names:
        return True
    else:
        return False


def print_parsed_data(userdata, groupdata):
    print("Users:\n")
    for user, role in userdata.items():
        print(" - {} (role: {})".format(user, role))
    print("\nGroups:\n")
    for group in groupdata:
        print(" - " + group)


def entry():
    '''Entry point'''
    args = _get_args()
    yoda_version = args.yoda_version if args.yoda_version is not None else common_config.get_default_yoda_version()
    userdata = parse_user_file(args.userfile)
    groupdata = parse_group_file(args.groupfile)

    if args.offline_check:
        print_parsed_data(userdata, groupdata)
        sys.exit(0)

    session = s.setup_session(yoda_version)
    rule_interface = RuleInterface(session, yoda_version)

    try:
        validation_errors = validate_data(rule_interface, args, userdata, groupdata)

        if len(validation_errors) > 0:
            _exit_with_validation_errors(validation_errors)
        elif args.verbose:
            print("No validation errors encountered.")

        if not args.online_check:
            apply_data(rule_interface, args, userdata, groupdata, args.verbose, args.dry_run)

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)

    finally:
        session.cleanup()


def parse_user_file(userfile):
    users = {}

    if not os.path.isfile(userfile):
        _exit_with_error("User file {} does not exist or is not a regular file.".format(userfile))
    with open(userfile, "r") as input:
        for line in input:
            fields = line.rstrip().split(":")
            if len(fields) != 2:
                _exit_with_error("Line \"{}\" in use file has invalid format.".format(line))
            if fields[0] not in ["manager", "member", "viewer"]:
                _exit_with_error("Role {} in user file is not a valid role.".format(fields[0]))
            username = fields[1].strip().lower()
            users[username] = fields[0]

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


def parse_group_file(groupfile):
    groups = []

    with _open_file_or_stdin(groupfile, "r") as input:
        for line in input:
            if line != "":
                groups.append(line.rstrip())

    if len(groups) == 0:
        _exit_with_error("Group file has no groups.")

    return groups


def _print_error(message):
    print("Error: {}".format(message), file=sys.stderr)


def _exit_with_error(message):
    _print_error(message)
    sys.exit(1)


def _exit_with_validation_errors(errors):
    for error in errors:
        print("Validation error: {}".format(error), file=sys.stderr)
    sys.exit(1)
