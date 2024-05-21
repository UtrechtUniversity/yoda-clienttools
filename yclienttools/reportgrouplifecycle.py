'''Generates a list of research groups, along with their creation date, expiration date (if available),
   lists of group managers, regular members, and readonly members. The report also shows whether each
   research compartment contains data, as well as whether its vault compartment contains data.'''

import argparse
import csv
import datetime
import itertools
import sys
from typing import Dict, List, Union

from irods.column import Like
from irods.message import (ET, XML_Parser_Type)
from irods.models import Collection, DataObject, User
from irods.session import iRODSSession
from yclienttools import common_args, common_config
from yclienttools import session as s


def entry():
    '''Entry point'''
    try:
        args = _get_args()
        yoda_version = args.yoda_version if args.yoda_version is not None else common_config.get_default_yoda_version()
        session = s.setup_session(yoda_version)
        if args.quasi_xml:
            ET(XML_Parser_Type.QUASI_XML, session.server_version)
        report_groups_lifecycle(args, session)
        session.cleanup()

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)


def _get_args() -> argparse.Namespace:
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-q", "--quasi-xml", default=False, action='store_true',
                        help='Enable Quasi-XML parser in order to be able to parse characters not supported by regular XML parser')
    common_args.add_default_args(parser)
    return parser.parse_args()


def _get_group_attributes(session: iRODSSession, group_name: str) -> Dict[str, Union[str, List[str]]]:
    """Retrieves a dictionary of attribute-values of group metadata.

       :param session: iRODS session
       :param group_name: group name

       :returns: dictionary of attribute-values. Values can be either strings, or lists of strings
                 for multi-value attributes
    """
    relevant_single_attributes = {"category", "subcategory", "expiration_date"}
    relevant_multiple_attributes = {"manager"}
    result: Dict[str, Union[str, List[str]]] = dict()
    group_objects = list(session.query(User).filter(
        User.name == group_name).filter(
        User.type == "rodsgroup").get_results())

    if len(group_objects) > 0:
        for attribute in relevant_multiple_attributes:
            result[attribute] = []
        for group_object in group_objects:
            obj = session.users.get(group_object[User.name])
            avus = obj.metadata.items()
            for avu in avus:
                if avu.name in relevant_single_attributes:
                    result[avu.name] = avu.value
                elif avu.name in relevant_multiple_attributes:
                    result[avu.name].append(avu.value)  # type: ignore

    return result


def _group_research_has_data(session: iRODSSession, group_name: str) -> int:
    """Returns boolean that indicates whether the research compartment of
       the group has any data (i.e. data objects or subcollections).
       if the group has no research department, None is returned.

       :param session: iRODS session
       :param group_name: group name

       :returns: number of data objects in research group
    """
    research_collection = f"/{session.zone}/home/{group_name}"
    return _collection_has_data(session, research_collection)


def _group_vault_has_data(session: iRODSSession, group_name: str) -> int:
    """Returns boolean that indicates whether the vault compartment of
       the group has any data (i.e. data objects or subcollections).
       If the group has no vault compartment, None is returned.

       :param session: iRODS session
       :param group_name: group name

       :returns: number of data objects in vault group

    """
    vault_collection = f"/{session.zone}/home/{group_name}".replace(
        "research-", "vault-", 1)
    return _collection_has_data(session, vault_collection)


def _collection_has_data(session: iRODSSession, coll_name: str) -> int:
    root_data_objects = session.query(Collection.name, DataObject.name).filter(
        Collection.name == coll_name).get_results()
    sub_data_objects = session.query(Collection.name, DataObject.name).filter(
        Like(Collection.name, coll_name + "/%")).get_results()
    sub_data_collections = session.query(Collection.name).filter(
        Like(Collection.name, coll_name + "/%")).get_results()
    return len(list(itertools.chain(root_data_objects,
                                    sub_data_objects,
                                    sub_data_collections)))


def _get_group_creation_date(session: iRODSSession, group_name: str) -> Union[datetime.datetime, None]:
    create_times = list(session.query(
        User.create_time).filter(
        User.name == group_name).get_results())
    return create_times[0][User.create_time] if len(create_times) else None


def _get_research_groups_list(session: iRODSSession) -> List[str]:
    groups = session.query(User).filter(User.type == 'rodsgroup').get_results()
    return [x[User.name]
            for x in groups if x[User.name].startswith("research-")]


def _get_regular_members(session: iRODSSession, group_name: str, attributes: Dict[str, Union[str, List[str]]]) -> List[str]:
    members_and_managers = session.user_groups.getmembers(group_name)
    return [
        member.name for member in members_and_managers if member.name + "#" + session.zone not in attributes["manager"]]


def _get_readonly_members(session: iRODSSession, group_name: str, attributes: Dict[str, Union[str, List[str]]]) -> List[str]:
    readonly_group = group_name.replace("research-", "read-", 1)
    return [u.name for u in session.user_groups.getmembers(readonly_group)]


def _get_group_managers(session: iRODSSession, group_name: str, attributes: Dict[str, Union[str, List[str]]]) -> List[str]:
    return [manager.split("#")[0] for manager in attributes["manager"]]


def _list_or_str_to_str(value: Union[str, List[str]]) -> str:
    if type(value) is str:
        return value
    else:
        return ";".join(value)


def report_groups_lifecycle(args: argparse.Namespace, session: iRODSSession):
    output = csv.writer(sys.stdout, delimiter=',')
    output.writerow(["Group name", "Category", "Subcategory",
                     "Group managers", "Regular members", "Read-only members",
                     "Creation date", "Expiration date", "Has research data", "Has vault data"])

    def _has_data_to_string(value):
        if value is None:
            return "N/A"
        else:
            return "yes" if value else "no"

    for group in sorted(_get_research_groups_list(session)):
        attributes = _get_group_attributes(session, group)
        category = attributes.get("category", "no category")
        subcategory = attributes.get("subcategory", "no subcategory")
        group_managers = _list_or_str_to_str(_get_group_managers(session, group, attributes))
        regular_members = _list_or_str_to_str(_get_regular_members(session, group, attributes))
        readonly_members = _list_or_str_to_str(_get_readonly_members(session, group, attributes))
        creation_date = _get_group_creation_date(session, group)
        creation_date_str = creation_date.strftime(
            "%Y-%m-%d") if creation_date is not None else "N/A"
        expiration_date = attributes.get("expiration_date", "N/A")
        research_has_data = _has_data_to_string(
            _group_research_has_data(session, group))
        vault_has_data = _has_data_to_string(
            _group_vault_has_data(session, group))
        output.writerow([group, category, subcategory,
                         group_managers, regular_members, readonly_members,
                         creation_date_str, expiration_date, research_has_data, vault_has_data])
