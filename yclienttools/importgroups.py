'''Creates a list of groups based on a CSV file'''
import argparse
import csv
import sys
import re

import dns.resolver as resolver

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

from yclienttools import common_queries
from yclienttools import common_rules as cr
from yclienttools import session as s
from yclienttools.exceptions import SizeNotSupportedException

# Based on yoda-batch-add script by Ton Smeele

def parse_csv_file(input_file):
    extracted_data = []

    with open(input_file, mode="r", encoding="utf-8-sig") as csv_file:

        dialect = csv.Sniffer().sniff(csv_file.read(), delimiters=';,')
        csv_file.seek(0)

        reader = csv.DictReader(
            csv_file,
            dialect=dialect,
            restval='',
            restkey='OTHERDATA')
        row_number = 1  # header row already read

        for label in _get_csv_predefined_labels():
            if label not in reader.fieldnames:
                _exit_with_error(
                    'CSV header is missing compulsory field "{}"'.format(label))

        duplicate_columns = _get_duplicate_columns(reader.fieldnames)
        if ( len(duplicate_columns) > 0 ):
            _exit_with_error("File has duplicate column(s): " + str(duplicate_columns) )

        for line in reader:
            row_number += 1
            rowdata, error = _process_csv_line(line)

            if error is None:
                extracted_data.append(rowdata)
            else:
                _exit_with_error("Data error in in row {}: {}".format(
                    str(row_number), error))

    return extracted_data


def _get_csv_predefined_labels():
    return ['category', 'subcategory', 'groupname']


def _get_duplicate_columns(fields_list):
    fields_seen = set()
    duplicate_fields = set()

    for field in fields_list:
        if ( field in _get_csv_predefined_labels() or
             field.startswith( ("manager:", "viewer:", "member:"))):
            if field in fields_seen:
                duplicate_fields.add(field)
            else:
                fields_seen.add(field)

    return duplicate_fields


def _process_csv_line(line):
    category = line['category'].strip().lower().replace('.', '')
    subcategory = line['subcategory'].strip()
    groupname = "research-" + line['groupname'].strip().lower()
    managers = []
    members = []
    viewers = []

    for column_name in line.keys():
        if column_name == '':
            return None, 'Column cannot have an empty label'
        elif column_name in _get_csv_predefined_labels():
            continue

        username = line.get(column_name)

        if isinstance(username, list):
            return None, "Data is present in an unlabelled column"

        username = username.strip().lower()

        if username == '':    # empty value
            continue
        elif not is_email(username):
            return None, 'Username "{}" is not a valid email address.'.format(
                username)
        elif not is_valid_domain(username.split('@')[1]):
            return None, 'Username "{}" failed DNS domain validation - domain does not exist or has no MX records.'.format(username)

        if column_name.lower().startswith('manager:'):
            managers.append(username)
        elif column_name.lower().startswith('member:'):
            members.append(username)
        elif column_name.lower().startswith('viewer:'):
            viewers.append(username)
        else:
            return None, "Column label '{}' is neither predefined nor a valid role label.".format(column_name)

    # perform additional data validations
    if (len(category) == 0) | (len(subcategory) == 0) | (len(groupname) == 0):
        return None, "Row has no group name, category or subcategory"

    if len(managers) == 0:
        return None, "Group must have a group manager"

    if not is_valid_category(category):
        return None, '"{}" is not a valid category name.'.format(category)

    if not is_valid_category(subcategory):
        return None, '"{}" is not a valid subcategory name.'.format(subcategory)

    if not is_valid_groupname(groupname):
        return None, '"{}" is not a valid group name.'.format(groupname)

    row_data = (category, subcategory, groupname, managers, members, viewers)
    return row_data, None


def _are_roles_equivalent(a,b):
    """Checks whether two roles are equivalent. Needed because Yoda and Yoda-clienttools
       use slightly different names for the roles."""
    r_role_names = [ "viewer", "reader" ]
    m_role_names = [ "member", "normal" ]

    if a == b:
        return True
    elif a in r_role_names and b in r_role_names:
        return True
    elif a in m_role_names and b in m_role_names:
        return True
    else:
        return False

def is_email(username):
    return re.search(r'@.*[^\.]+\.[^\.]+$', username) is not None

@lru_cache(maxsize=100)
def is_valid_domain(domain):
    try:
      return bool(resolver.query(domain, 'MX'))
    except (resolver.NXDOMAIN, resolver.NoAnswer):
      return False

def is_valid_category(name):
    """Is this name a valid (sub)category name?"""
    return re.search(r"^[a-zA-Z0-9\-_]+$", name) is not None

def is_valid_groupname(name):
    """Is this name a valid group name (prefix such as "research-" can be omitted"""
    return re.search(r"^[a-zA-Z0-9\-]+$", name) is not None

def is_internal_user(username, internal_domains):
    for domain in internal_domains:
        domain_pattern = '@{}$'.format(domain)
        if re.search(domain_pattern, username) is not None:
            return True

    return False


def validate_data(session, args, data):
    errors = []
    for (category, subcategory, groupname, managers, members, viewers) in data:
        if cr.call_uuGroupExists(session, groupname) and not args.allow_update:
            errors.append('Group "{}" already exists'.format(groupname))

        for user in managers + members + viewers:
            if not is_internal_user(user, args.internal_domains.split(",")):
                # ensure that external users already have an iRODS account
                # we do not want to be the actor that creates them
                if not cr.call_uuUserExists(session, user):
                    errors.append(
                        'Group {} has nonexisting external user {}'.format(groupname, user))

    return errors


def apply_data(session, args, data):
    for (category, subcategory, groupname, managers, members, viewers) in data:
        new_group = False

        if args.verbose:
            print('Adding and updating group: {}'.format(groupname))

        # First create the group. Note that the rodsadmin actor will become a
        # groupmanager.
        [status, msg] = cr.call_uuGroupAdd(
            session, groupname, category, subcategory, '', 'unspecified')

        if ((status == '-1089000') | (status == '-809000')) and args.allow_update:
            print(
                'WARNING: group "{}" not created, it already exists'.format(groupname))
        elif status != '0':
            _exit_with_error(
                "Error while attempting to create group {}. Status/message: {} / {}".format(
                    groupname,
                    status,
                    msg))
        else:
            new_group = True

        # Now add the users and set their role if other than member
        allusers = managers + members + viewers
        for username in list(set(allusers)):   # duplicates removed
            currentrole = cr.call_uuGroupGetMemberType(session, groupname, username)

            if currentrole == "none":
                [status, msg] = cr.call_uuGroupUserAdd(session, groupname, username)

                if status == '0':
                     currentrole = "member"
                     if args.verbose:
                         print("Notice: added user {} to group {}".format(username,groupname))
                else:
                    print("Warning: error occurred while attempting to add user {} to group {}".format(
                         username,
                         groupname))
                    print("Status: {} , Message: {}".format(status, msg))
            else:
                if args.verbose:
                    print("Notice: user {} is already present in group {}.".format(username,groupname))

            # Set requested role. Note that user could be listed in multiple roles.
            # In case of multiple roles, manager takes precedence over normal,
            # and normal over reader
            role = 'reader'
            if username in members:
                role = 'normal'
            if username in managers:
                role = 'manager'

            if _are_roles_equivalent(role, currentrole):
                if args.verbose:
                    print("Notice: user {} already has role {} in group {}.".format(username, role, groupname))
            else:
                [status, msg] = cr.call_uuGroupUserChangeRole(
                    session, groupname, username, role)
                if status == '0':
                    if args.verbose:
                        print("Notice: changed role of user {} in group {} to {}".format(username, groupname, role))
                else:
                    print(
                        "Warning: error while attempting to change role of user {} in group {} to {}".format(
                            username,
                            groupname,
                            role))
                    print("Status: {} , Message: {}".format(status, msg))

        # Always remove the rods user for new groups, unless it is in the
        # CSV file.
        if ( new_group and "rods" not in allusers and
             cr.call_uuGroupGetMemberType(session, groupname, "rods") != "none" ):
             (status,msg) = cr.call_uuGroupUserRemove(session, groupname, "rods")
             if status == "0":
                 if args.verbose:
                     print("Notice: removed rods user from group " + groupname)
             else:
                 if status !=0:
                     print ("Warning: error while attempting to remove user {} from group {}".format(user,groupname))
                     print("Status: {} , Message: {}".format(status, msg))

        # Remove users not in sheet
        if args.delete:

            try:
                currentusers = cr.call_uuGroupGetMembers(session, groupname)
            except SizeNotSupportedException:
                print("Unable to check whether members of group {} need to be deleted.".format(groupname))
                print("Number of current members group is too large.")
                continue

            for user in currentusers:
                if user not in allusers:
                    if user in managers:
                        if len(managers) == 1:
                            print("Error: cannot remove user {} from group {}, because he/she is the only group manager".format(
                                user,groupname))
                            continue
                        else:
                            managers.remove(user)
                    if args.verbose:
                        print("Removing user {} from group {}".format(user,groupname))
                    (status,msg) = cr.call_uuGroupUserRemove(session, groupname, user)
                    if status != "0":
                        print ("Warning: error while attempting to remove user {} from group {}".format(user,groupname))
                        print("Status: {} , Message: {}".format(status, msg))


def print_parsed_data(data):
    print('Parsed data:')
    print()

    if data is None:
        print('No data loaded')
    else:
        for (category, subcategory, groupname,
             managers, members, viewers) in data:
            print("Category: {}".format(category))
            print("Subcategory: {}".format(subcategory))
            print("Group: {}".format(groupname))
            print("Managers: {}".format(','.join(managers)))
            print("Members: {}".format(','.join(members)))
            print("Readonly members: {}".format(','.join(viewers)))
            print()


def entry():
    '''Entry point'''
    args = _get_args()
    data = parse_csv_file(args.csvfile)

    if args.offline_check or args.verbose:
        print_parsed_data(data)

    if args.delete and not args.allow_update:
        _exit_with_error("Using the --delete option without the --allow-update option is not supported.")

    if args.offline_check:
        sys.exit(0)

    session = s.setup_session()

    try:
        validation_errors = validate_data(session, args, data)

        if len(validation_errors) > 0:
            _exit_with_validation_errors(validation_errors)

        if not args.online_check:
            apply_data(session, args, data)

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)

    finally:
        session.cleanup()


def _get_args():
    '''Parse command line arguments'''

    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=_get_format_help_text(),
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('csvfile', help='Name of the CSV file')
    parser.add_argument('-i', '--internal-domains', required=True,
                        help='Comma-separated list of internal email domains to the Yoda server')
    actiongroup = parser.add_mutually_exclusive_group()
    actiongroup.add_argument('--offline-check', '-c', action='store_true',
                             help='Check mode (offline): verify CSV format only. Does not connect to iRODS and does not create groups')
    actiongroup.add_argument('--online-check', '-C', action='store_true',
                             help='Check mode (online): verify CSV format and that groups do not exist. Does not create groups.')
    parser.add_argument('--allow-update', "-u", action='store_true', default=False,
                        help='Allows existing groups to be updated')
    parser.add_argument('--delete', '-d', action='store_true', default=False,
                        help='Delete group members not in CSV file')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show information as extracted from CSV file')

    return parser.parse_args()


def _get_format_help_text():
    return '''
        The CSV file is expected to include the following labels in its header (the first row):
        'category'    = category for the group
        'subcategory' = subcategory for the group
        'groupname'   = name of the group (without the "research-" prefix)

        The remainder of the columns should have a label that starts with a prefix which
        indicates the role of each group member:

        'manager:'    = user that will be given the role of manager
        'member:'     = user that will be given the role of member with read/write
        'viewer:'     = user that will be given the role of viewer with read

        Notes:
        - Columns may appear in any order
        - Empty data cells are ignored: groups can differ in number of members

        Example:
        category,subcategory,groupname,manager:manager,member:member1,member:member2
        departmentx,teama,groupteama,m.manager@example.com,m.member@example.com,n.member@example.com
        departmentx,teamb,groupteamb,m.manager@example.com,p.member@example.com,
    '''


def _exit_with_error(message):
    print("Error: {}".format(message), file=sys.stderr)
    sys.exit(1)


def _exit_with_validation_errors(errors):
    for error in errors:
        print("Validation error: {}".format(error), file=sys.stderr)
    sys.exit(1)
