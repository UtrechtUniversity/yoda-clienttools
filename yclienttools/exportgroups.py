'''Exports groups and group membership into a CSV file'''
import argparse
import csv
import sys
from typing import Dict, List, Tuple
from irods.session import iRODSSession
from irods.models import User, UserGroup
from yclienttools import session as s
from yclienttools.common_queries import get_group_attributes, get_prefixed_groups

from yclienttools import common_args, common_config


def entry() -> None:
    '''Entry point'''
    max_counts = {}
    try:
        args = _get_args()
        yoda_version = args.yoda_version if args.yoda_version is not None else common_config.get_default_yoda_version()
        session = s.setup_session(yoda_version)

        try:
            data, max_counts = _get_all_visible_groups(session)
        finally:
            session.cleanup()

        # Write to csv
        _write_csv(data, max_counts)
    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)


def _get_all_visible_groups(session: iRODSSession) -> Tuple[Dict, Dict]:
    """Gather all groups that the current user has access to information on

    :param session: iRods session
    :return: Lists of group information in dictionaries, max counts for each member type
    """
    group_names = get_prefixed_groups(session, "research-")
    outputdata = []
    max_counts = {}
    max_counts["manager"] = 0
    max_counts["member"] = 0
    max_counts["viewer"] = 0

    for group in sorted(group_names):
        group_rowdata = _get_group_rowdata(session, group)
        group_rowdata["groupname"] = _get_group_shortname(group)

        for user_type in {"manager", "member", "viewer"}:
            max_counts[user_type] = max(max_counts[user_type], len(group_rowdata[user_type]))
        outputdata.append(group_rowdata)

    return outputdata, max_counts


def _write_csv(data: List[Dict], max_counts: Dict):
    """Write contents to csv

    :param data: List where each entry is dictionary with the group's info
    :param max_counts: Max counts for each type of member in group
    """
    output_write_header = csv.writer(sys.stdout, delimiter=',')
    output_write_header.writerow(_get_columns(max_counts))

    output = csv.writer(sys.stdout, delimiter=',', quoting=csv.QUOTE_NOTNULL)

    for rowdata in data:
        output_row = ([rowdata['category'], rowdata['subcategory'], rowdata['groupname'],
                      rowdata.get('schema_id', None), rowdata.get('expiration_date', None)])
        for user_type in ("manager", "member", "viewer"):
            output_row += rowdata[user_type] + [None] * (max_counts[user_type] - len(rowdata[user_type]))
        output.writerow(output_row)


def _get_group_rowdata(session: iRODSSession, group: str) -> Dict:
    attributes = get_group_attributes(session, group, {"category", "subcategory", "expiration_date", "schema_id"}, {"manager"})
    attributes["manager"] = [user.split('#')[0] for user in attributes["manager"]]
    attributes["member"] = list(set(_get_group_members(session, group)) - set(attributes["manager"]))
    attributes["viewer"] = _get_group_read_members(session, group)
    return attributes


def _get_group_shortname(group: str) -> str:
    if group.startswith("research-"):
        return group[9:]


def _get_group_read_members(session: iRODSSession, group: str) -> List[str]:
    group = "read-" + _get_group_shortname(group)
    members = []

    iter = list(session.query(User).filter(
        UserGroup.name == group).filter(
        User.type != "rodsgroup").get_results())

    for row in iter:
        user = row[User.name]
        if user != group:
            members.append(user)

    return members


def _get_group_members(session: iRODSSession, group: str) -> List[str]:
    """Get group memberships"""
    members = []
    iter = list(session.query(User).filter(
        UserGroup.name == group).filter(
        User.type != "rodsgroup").get_results())

    for row in iter:
        user = row[User.name]
        if group not in (user, 'rodsadmin', 'public'):
            members.append(user)

    return members


def _get_columns(max_counts: Dict) -> List[str]:
    return (['category', 'subcategory', 'groupname', 'schema_id', 'expiration_date']
            + ['manager'] * max_counts['manager'] + ['member'] * max_counts['member'] + ['viewer'] * max_counts["viewer"])


def _get_args() -> argparse.Namespace:
    '''Parse command line arguments'''

    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=_get_format_help_text(),
        formatter_class=argparse.RawTextHelpFormatter)
    common_args.add_default_args(parser)
    return parser.parse_args()


def _get_format_help_text() -> str:
    return '''
        This script only supports Yoda versions 1.9 and higher.
        The CSV returned to stdout is formatted to have the following labels in its header (the first row):
        'category'        = category for the group
        'subcategory'     = subcategory for the group
        'groupname'       = name of the group (without the "research-" prefix)

        These labels may optionally be included:
        'expiration_date' = expiration date for the group. Can only be set when the group is first created.
        'schema_id'       = schema id for the group. Can only be set when the group is first created.

        The remainder of the columns are labels that indicate the role of each group member:
        'manager'         = user that will be given the role of manager
        'member'          = user that will be given the role of member with read/write
        'viewer'          = user that will be given the role of viewer with read

        Example:
        category,subcategory,groupname,manager,member,expiration_date,schema_id
        departmentx,teama,groupteama,m.manager@example.com,m.member@example.com,2055-01-01,default-3
        departmentx,teamb,groupteamb,m.manager@example.com,p.member@example.com,,
    '''
