'''Generates a list of research and deposit groups, along with their creation date, expiration date
   (if available), lists of group managers, regular members, and readonly members. The report also
   shows whether each research compartment contains data, as well as whether its vault compartment
   contains data.

   The report can optionally include size and last modified date of both the research/deposit and
   vault collection, as well as revisions.
'''

import argparse
import csv
import datetime
import itertools
import sys
from typing import Dict, List, Union

import humanize
from irods.column import Like
from irods.message import (ET, XML_Parser_Type)
from irods.models import Collection, DataObject, User
from irods.session import iRODSSession
from yclienttools import common_args, common_config, session as s
from yclienttools.common_queries import collection_exists, get_collection_contents_last_modified, get_collection_size
from yclienttools.options import GroupByOption


def entry():
    '''Entry point'''
    try:
        args = _get_args()
        yoda_version = args.yoda_version if args.yoda_version is not None else common_config.get_default_yoda_version()
        # Use session with increased session timeout because querying modification times
        # can be time consuming on large environments.
        session = s.setup_session(yoda_version, session_timeout=600)
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
    parser.add_argument("-s", "--size", default=False, action='store_true',
                        help='Include size of research/deposit collection, vault collection and revisions in output')
    parser.add_argument("-H", "--human-readable", default=False, action='store_true',
                        help='Report sizes in human-readable figures (only relevant in combination with --size parameter)')
    parser.add_argument("-m", "--modified", default=False, action='store_true',
                        help='Include last modified date research/deposit collection, revisions and vault collection in output')
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
    return _collection_has_data(session, _get_research_group_collection(session, group_name))


def _group_vault_has_data(session: iRODSSession, group_name: str) -> int:
    """Returns boolean that indicates whether the vault compartment of
       the group has any data (i.e. data objects or subcollections).
       If the group has no vault compartment, None is returned.

       :param session: iRODS session
       :param group_name: group name

       :returns: number of data objects in vault group

    """
    return _collection_has_data(session, _get_vault_group_collection(session, group_name))


def _get_vault_group_collection(session: iRODSSession, group_name: str) -> str:
    if group_name.startswith("research-"):
        return f"/{session.zone}/home/{group_name}".replace(
            "research-", "vault-", 1)
    elif group_name.startswith("deposit-"):
        return f"/{session.zone}/home/{group_name}".replace(
            "deposit-", "vault-", 1)
    else:
        raise Exception("Unable to get vault group for group " + group_name)


def _get_research_group_collection(session: iRODSSession, group_name: str) -> str:
    return f"/{session.zone}/home/{group_name}"


def _get_revision_group_collection(session: iRODSSession, group_name: str) -> str:
    return f"/{session.zone}/yoda/revisions/{group_name}"


def _get_research_size(session: iRODSSession, group_name: str) -> Union[int, None]:
    collection = _get_research_group_collection(session, group_name)
    if collection_exists(session, collection):
        return _get_collection_size_for_glr(session, collection)
    else:
        return None


def _get_vault_size(session: iRODSSession, group_name: str) -> Union[int, None]:
    collection = _get_vault_group_collection(session, group_name)
    if collection_exists(session, collection):
        return _get_collection_size_for_glr(session, collection)
    else:
        return None


def _get_revisions_size(session: iRODSSession, group_name: str) -> Union[int, None]:
    collection = _get_revision_group_collection(session, group_name)
    if collection_exists(session, collection):
        return _get_collection_size_for_glr(session, collection)
    else:
        return None


def _get_collection_size_for_glr(session: iRODSSession, collection_name: str) -> int:
    return get_collection_size(session, collection_name, True, GroupByOption.none, False)['all']


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


def _get_relevant_groups_list(session: iRODSSession) -> List[str]:
    groups = session.query(User).filter(User.type == 'rodsgroup').get_results()
    return [x[User.name]
            for x in groups if x[User.name].startswith(("research-", "deposit-"))]


def _get_regular_members(session: iRODSSession, group_name: str, attributes: Dict[str, Union[str, List[str]]]) -> List[str]:
    members_and_managers = session.groups.getmembers(group_name)
    return [
        member.name for member in members_and_managers if member.name + "#" + session.zone not in attributes["manager"]]


def _get_readonly_members(session: iRODSSession, group_name: str, attributes: Dict[str, Union[str, List[str]]]) -> List[str]:
    readonly_group = group_name.replace("research-", "read-", 1)
    return [u.name for u in session.groups.getmembers(readonly_group)]


def _get_group_managers(session: iRODSSession, group_name: str, attributes: Dict[str, Union[str, List[str]]]) -> List[str]:
    return [manager.split("#")[0] for manager in attributes["manager"]]


def _get_columns(args: argparse.Namespace) -> List[str]:
    base_cols = ["Group name", "Category", "Subcategory",
                 "Group managers", "Regular members", "Read-only members",
                 "Creation date", "Expiration date", "Has research data", "Has vault data"]

    if args.size:
        extra_cols = ["Research collection size", "Vault collection size", "Revisions size"]
    else:
        extra_cols = []

    if args.modified:
        extra_cols.append("Research last modified")
        extra_cols.append("Vault last modified")
        extra_cols.append("Revisions last modified")

    result = base_cols
    result.extend(extra_cols)
    return result


def _list_or_str_to_str(value: Union[str, List[str]]) -> str:
    if type(value) is str:
        return value
    else:
        return ";".join(value)


def _size_to_str(value: Union[int, None], human_readable: bool) -> str:
    if value is None:
        return "N/A"
    elif human_readable:
        return humanize.naturalsize(value, binary=True)
    else:
        return str(value)


def _timestamp_to_date_str(value: Union[datetime.datetime, None]) -> str:
    return "N/A" if value is None else value.strftime("%Y-%m-%d")


def report_groups_lifecycle(args: argparse.Namespace, session: iRODSSession):
    output = csv.writer(sys.stdout, delimiter=',')
    output.writerow(_get_columns(args))

    def _has_data_to_string(value):
        if value is None:
            return "N/A"
        else:
            return "yes" if value else "no"

    for group in sorted(_get_relevant_groups_list(session)):
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
        rowdata = [group, category, subcategory,
                   group_managers, regular_members, readonly_members,
                   creation_date_str, expiration_date, research_has_data, vault_has_data]

        if args.size:
            rowdata.append(_size_to_str(_get_research_size(session, group), args.human_readable))
            rowdata.append(_size_to_str(_get_vault_size(session, group), args.human_readable))
            rowdata.append(_size_to_str(_get_revisions_size(session, group), args.human_readable))

        if args.modified:
            rowdata.append(_timestamp_to_date_str(
                get_collection_contents_last_modified(session, _get_research_group_collection(session, group))))
            rowdata.append(_timestamp_to_date_str(
                get_collection_contents_last_modified(session, _get_vault_group_collection(session, group))))
            rowdata.append(_timestamp_to_date_str(
                get_collection_contents_last_modified(session, _get_revision_group_collection(session, group))))

        output.writerow(rowdata)
