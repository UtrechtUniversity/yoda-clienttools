'''Creates a list of groups based on a CSV file'''
import argparse
import csv
import sys
import re
from datetime import datetime

import dns.resolver as resolver

from yclienttools import common_args, common_config

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

from yclienttools import session as s
from yclienttools.common_rules import RuleInterface
from yclienttools.exceptions import SizeNotSupportedException

# Based on yoda-batch-add script by Ton Smeele


def parse_csv_file(input_file, args, yoda_version):
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

        for label in _get_csv_required_labels():
            if label not in reader.fieldnames:
                _exit_with_error(
                    'CSV header is missing compulsory field "{}"'.format(label))

        duplicate_columns = _get_duplicate_columns(
            reader.fieldnames, yoda_version)
        if (len(duplicate_columns) > 0):
            _exit_with_error(
                "File has duplicate column(s): " + str(duplicate_columns))

        for line in reader:
            row_number += 1
            rowdata, error = _process_csv_line(line, args, yoda_version)

            if error is None:
                extracted_data.append(rowdata)
            else:
                _exit_with_error("Data error in row {}: {}".format(
                    str(row_number), error))

    return extracted_data


def _get_csv_required_labels():
    return ['category', 'subcategory', 'groupname']


def _get_csv_1_9_exclusive_labels():
    """Returns labels that can only appear with yoda version 1.9 and higher."""
    return ['expiration_date', 'schema_id']


def _get_csv_predefined_labels(yoda_version):
    if yoda_version in ('1.7', '1.8'):
        return ['category', 'subcategory', 'groupname']
    else:
        return ['category', 'subcategory', 'groupname', 'expiration_date', 'schema_id']


def _get_duplicate_columns(fields_list, yoda_version):
    fields_seen = set()
    duplicate_fields = set()

    for field in fields_list:
        if (field in _get_csv_predefined_labels(yoda_version) or
                field.startswith(("manager:", "viewer:", "member:"))):
            if field in fields_seen:
                duplicate_fields.add(field)
            else:
                fields_seen.add(field)

    return duplicate_fields


def _process_csv_line(line, args, yoda_version):
    category = line['category'].strip().lower().replace('.', '')
    subcategory = line['subcategory'].strip()
    groupname = "research-" + line['groupname'].strip().lower()
    schema_id = line['schema_id'] if 'schema_id' in line else ''
    expiration_date = line['expiration_date'] if 'expiration_date' in line else ''
    managers = []
    members = []
    viewers = []

    for column_name in line.keys():
        if column_name == '':
            return None, 'Column cannot have an empty label'
        elif yoda_version in ('1.7', '1.8') and column_name in _get_csv_1_9_exclusive_labels():
            return None, 'Column "{}" is only supported in Yoda 1.9 and higher'.format(column_name)
        elif column_name in _get_csv_predefined_labels(yoda_version):
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
        elif not (args.no_validate_domains or is_valid_domain(username.split('@')[1])):
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

    if not is_valid_schema_id(schema_id):
        return None, '"{}" is not a valid schema id.'.format(schema_id)

    if not is_valid_expiration_date(expiration_date):
        return None, '"{}" is not a valid expiration date.'.format(expiration_date)

    row_data = (category, subcategory, groupname, managers,
                members, viewers, schema_id, expiration_date)
    return row_data, None


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


def is_valid_expiration_date(expiration_date):
    """Validation of expiration date.

    :param expiration_date: String containing date that has to be validated

    :returns: Indication whether expiration date is an accepted value
    """
    # Copied from rule_group_expiration_date_validate
    if expiration_date in ["", "."]:
        return True

    try:
        if expiration_date != datetime.strptime(expiration_date, "%Y-%m-%d").strftime('%Y-%m-%d'):
            raise ValueError

        # Expiration date should be in the future
        if expiration_date <= datetime.now().strftime('%Y-%m-%d'):
            raise ValueError
        return True
    except ValueError:
        return False


def is_valid_schema_id(schema_id):
    """Is this schema at least a correctly formatted schema-id?"""
    if schema_id == "":
        return True
    return re.search(r"^[a-zA-Z0-9\-]+\-[0-9]+$", schema_id) is not None


def validate_data(rule_interface, args, data):
    errors = []
    for (category, subcategory, groupname, managers, members, viewers, schema_id, expiration_date) in data:
        if rule_interface.call_uuGroupExists(groupname) and not args.allow_update:
            errors.append('Group "{}" already exists'.format(groupname))

        for user in managers + members + viewers:
            if not is_internal_user(user, args.internal_domains.split(",")):
                # ensure that external users already have an iRODS account
                # we do not want to be the actor that creates them (unless
                # we are creating them in the name of a creator user)
                if not rule_interface.call_uuUserExists(user) and not args.creator_user:
                    errors.append(
                        'Group {} has nonexisting external user {}'.format(groupname, user))

    return errors


def apply_data(rule_interface, args, data):
    for (category, subcategory, groupname, managers, members, viewers, schema_id, expiration_date) in data:
        new_group = False

        if args.verbose:
            print('Adding and updating group: {}'.format(groupname))

        # First create the group. Note that the rodsadmin actor will become a
        # groupmanager.
        [status, msg] = rule_interface.call_uuGroupAdd(
            groupname, category, subcategory, '', 'unspecified', schema_id, expiration_date)

        if ((status == '-1089000') | (status == '-809000')) and args.allow_update:
            print(
                'WARNING: group "{}" not created, it already exists'.format(groupname))
            if schema_id != '':
                print(
                    'WARNING: group property "schema_id" not updated, as it can only be specified when the group is first created')
        elif status != '0':
            _exit_with_error(
                'Error while attempting to create group "{}". Status/message: {} / {}'.format(
                    groupname,
                    status,
                    msg))
        else:
            new_group = True

        # Now add the users and set their role if other than member
        allusers = managers + members + viewers
        for username in list(set(allusers)):   # duplicates removed
            currentrole = rule_interface.call_uuGroupGetMemberType(
                groupname, username)

            if currentrole == "none":
                if args.creator_user:
                    [status, msg] = rule_interface.call_uuGroupUserAddByOtherCreator(
                        groupname, username, args.creator_user, args.creator_zone)
                else:
                    [status, msg] = rule_interface.call_uuGroupUserAdd(
                        groupname, username)

                if status == '0':
                    currentrole = "member"
                    if args.verbose:
                        print("Notice: added user {} to group {}".format(
                            username, groupname))
                else:
                    print("Warning: error occurred while attempting to add user {} to group {}".format(
                        username,
                        groupname))
                    print("Status: {} , Message: {}".format(status, msg))
            else:
                if args.verbose:
                    print("Notice: user {} is already present in group {}.".format(
                        username, groupname))

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
                    print("Notice: user {} already has role {} in group {}.".format(
                        username, role, groupname))
            else:
                [status, msg] = rule_interface.call_uuGroupUserChangeRole(
                    groupname, username, role)
                if status == '0':
                    if args.verbose:
                        print("Notice: changed role of user {} in group {} to {}".format(
                            username, groupname, role))
                else:
                    print(
                        "Warning: error while attempting to change role of user {} in group {} to {}".format(
                            username,
                            groupname,
                            role))
                    print("Status: {} , Message: {}".format(status, msg))

        # Always remove the rods user for new groups, unless it is in the
        # CSV file.
        if (new_group and "rods" not in allusers and
                rule_interface.call_uuGroupGetMemberType(groupname, "rods") != "none"):
            (status, msg) = rule_interface.call_uuGroupUserRemove(groupname, "rods")
            if status == "0":
                if args.verbose:
                    print("Notice: removed rods user from group " + groupname)
            else:
                if status != 0:
                    print("Warning: error while attempting to remove user rods from group {}".format(
                        groupname))
                    print("Status: {} , Message: {}".format(status, msg))

        # Update expiration date if applicable
        if not new_group and expiration_date not in ['', '.'] and args.allow_update:
            [status, msg] = rule_interface.call_uuGroupModify(
                groupname, "expiration_date", expiration_date)
            if status == "0":
                if args.verbose:
                    print("Notice: updated expiration date to {} for group {}".format(
                        expiration_date, groupname))
            else:
                print("Warning: error while attempting to update expiration date to {} for group {}".format(
                    expiration_date, groupname))
                print("Status: {} , Message: {}".format(status, msg))

        # Remove users not in sheet
        if args.delete:

            try:
                currentusers = rule_interface.call_uuGroupGetMembers(groupname)
            except SizeNotSupportedException:
                print("Unable to check whether members of group {} need to be deleted.".format(
                    groupname))
                print("Number of current members group is too large.")
                continue

            for user in currentusers:
                if user not in allusers:
                    if user in managers:
                        if len(managers) == 1:
                            print("Error: cannot remove user {} from group {}, because he/she is the only group manager".format(
                                user, groupname))
                            continue
                        else:
                            managers.remove(user)
                    if args.verbose:
                        print("Removing user {} from group {}".format(
                            user, groupname))
                    (status, msg) = rule_interface.call_uuGroupUserRemove(
                        groupname, user)
                    if status != "0":
                        print("Warning: error while attempting to remove user {} from group {}".format(
                            user, groupname))
                        print("Status: {} , Message: {}".format(status, msg))


def print_parsed_data(data):
    print('Parsed data:')
    print()

    if data is None:
        print('No data loaded')
    else:
        for (category, subcategory, groupname,
             managers, members, viewers, schema_id, expiration_date) in data:
            print("Category: {}".format(category))
            print("Subcategory: {}".format(subcategory))
            print("Group: {}".format(groupname))
            print("Managers: {}".format(','.join(managers)))
            print("Members: {}".format(','.join(members)))
            print("Readonly members: {}".format(','.join(viewers)))
            print("Schema Id: {}".format(schema_id))
            print("Expiration Date: {}".format(expiration_date))
            print()


def entry():
    '''Entry point'''
    args = _get_args()
    yoda_version = args.yoda_version if args.yoda_version is not None else common_config.get_default_yoda_version()
    data = parse_csv_file(args.csvfile, args, yoda_version)

    if args.offline_check or args.verbose:
        print_parsed_data(data)

    if args.delete and not args.allow_update:
        _exit_with_error(
            "Using the --delete option without the --allow-update option is not supported.")

    if (args.creator_user and not args.creator_zone) or (not args.creator_user and args.creator_zone):
        _exit_with_error(
            "Using the --creator-user option without the --creator-zone option is not supported.")

    if (args.creator_user and (yoda_version in ('1.7', '1.8'))):
        _exit_with_error(
            "The --creator-user and --creator-zone options are only supported with Yoda versions 1.9 and higher.")

    if args.offline_check:
        sys.exit(0)

    session = s.setup_session(yoda_version)
    rule_interface = RuleInterface(session, yoda_version)

    try:
        validation_errors = validate_data(rule_interface, args, data)

        if len(validation_errors) > 0:
            _exit_with_validation_errors(validation_errors)

        if not args.online_check:
            apply_data(rule_interface, args, data)

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
    common_args.add_default_args(parser)
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
    parser.add_argument('--no-validate-domains', '-n', action='store_true',
                        help='Do not validate email address domains')
    parser.add_argument('--creator-user', type=str,
                        help='User who creates user (only available in Yoda 1.9 and higher)')
    parser.add_argument('--creator-zone', type=str,
                        help='Zone of the user who creates user (only available in Yoda 1.9 and higher)')
    return parser.parse_args()


def _get_format_help_text():
    return '''
        The CSV file is expected to include the following labels in its header (the first row):
        'category'        = category for the group
        'subcategory'     = subcategory for the group
        'groupname'       = name of the group (without the "research-" prefix)

        For Yoda versions 1.9 and higher, these labels can optionally be included:
        'expiration_date' = expiration date for the group. Can only be set when the group is first created.
        'schema_id'       = schema id for the group. Can only be set when the group is first created.

        The remainder of the columns should have a label that starts with a prefix which
        indicates the role of each group member:

        'manager:'        = user that will be given the role of manager
        'member:'         = user that will be given the role of member with read/write
        'viewer:'         = user that will be given the role of viewer with read

        Notes:
        - Columns may appear in any order
        - Empty data cells are ignored: groups can differ in number of members

        Example:
        category,subcategory,groupname,manager:manager,member:member1,member:member2
        departmentx,teama,groupteama,m.manager@example.com,m.member@example.com,n.member@example.com
        departmentx,teamb,groupteamb,m.manager@example.com,p.member@example.com,

        Example Yoda 1.9 and higher:
        category,subcategory,groupname,manager:manager,member:member1,expiration_date,schema_id
        departmentx,teama,groupteama,m.manager@example.com,m.member@example.com,2025-01-01,default-2
        departmentx,teamb,groupteamb,m.manager@example.com,p.member@example.com,,
    '''


def _exit_with_error(message):
    print("Error: {}".format(message), file=sys.stderr)
    sys.exit(1)


def _exit_with_validation_errors(errors):
    for error in errors:
        print("Validation error: {}".format(error), file=sys.stderr)
    sys.exit(1)
