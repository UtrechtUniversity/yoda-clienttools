'''Generates a list of research and deposit groups. The report lists the amount of replica data in each research group
   collection, along with its vault group collection and revisions collection, split across old and new data. Data objects
   that have a replica that was modified after the user-provided cutoff date are considered 'new'. Data objects that do not
   have any replica that was modified after the user-provided cutoff date are considered 'old'.
'''

import argparse
import csv
import sys
from datetime import datetime
from typing import Dict, List, Union

import humanize
from irods.message import (ET, XML_Parser_Type)
from irods.models import Collection, DataObject, User
from irods.session import iRODSSession
from yclienttools import common_args, common_config, session as s
from yclienttools.common_queries import collection_exists, get_collections_in_root


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
        report_oldvsnewdata(args, session)
        session.cleanup()

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)


def _print_v(message: str) -> None:
    print(message, file=sys.stderr)


def _get_args() -> argparse.Namespace:
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-c", "--aggregate-by-category", default=False, action='store_true',
                        help='Aggregate size data by category rather than by group')
    parser.add_argument("-q", "--quasi-xml", default=False, action='store_true',
                        help='Enable Quasi-XML parser in order to be able to parse characters not supported by regular XML parser')
    parser.add_argument("-d", "--days-ago", default=4 * 365, type=int,
                        help="Cutoff date for dividing data in old vs. new data, in terms of number of days ago.")
    parser.add_argument("-e", "--environment", type=str, default=None,
                        help="Contents of environment column to add to output, so that output of multiple Yoda environments can be concatenated.")
    parser.add_argument("-H", "--human-readable", default=False, action='store_true',
                        help='Report sizes in human-readable figures')
    parser.add_argument("-p", "--progress", action='store_true', default=False,
                        help="Print progress updates")
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


def _get_relevant_groups_list(session: iRODSSession) -> List[str]:
    groups = session.query(User).filter(User.type == 'rodsgroup').get_results()
    return [x[User.name]
            for x in groups if x[User.name].startswith(("research-", "deposit-"))]


def _get_columns(args: argparse.Namespace) -> List[str]:
    columns = ["Group name", "Category", "Subcategory",
               "Research collection size (both)", "Vault collection size (both)", "Revisions size (both)", "Total size (both)",
               "Research collection size (old data)", "Vault collection size (old data)", "Revisions size (old data)", "Total size (old data)",
               "Research collection size (new data)", "Vault collection size (new data)", "Revisions size (new data)", "Total size (new data)"]
    return columns if args.environment is None else ["Environment"] + columns


def _size_to_str(value: Union[int, None], human_readable: bool) -> str:
    if value is None:
        return "N/A"
    elif human_readable:
        return humanize.naturalsize(value, binary=True)
    else:
        return str(value)


def _get_group_rowdata(session: iRODSSession, group: str, environment: Union[str, None]):
    attributes = _get_group_attributes(session, group)

    rowdata = {"Group name": group}

    # Group should always have one category and subcategory. Checking for no AVU or multiple
    # ones is just so that script does not break on unexpected category metadata.
    categories = attributes.get("category", "no category")
    subcategories = attributes.get("subcategory", "no subcategory")
    rowdata["Category"] = categories if isinstance(categories, str) else categories[0]
    rowdata["Subcategory"] = subcategories if isinstance(subcategories, str) else subcategories[0]

    if environment is not None:
        rowdata["Environment"] = environment

    return rowdata


def get_collection_data(session: iRODSSession,
                        root_collection: str,
                        cutoff_timestamp: int,
                        column_label: str,
                        print_progress: bool) -> Dict[str, int]:

    old_data_label = column_label + " (old data)"
    new_data_label = column_label + " (new data)"
    both_data_label = column_label + " (both)"

    results = {old_data_label: 0,
               new_data_label: 0,
               both_data_label: 0}

    if not collection_exists(session, root_collection):
        return results

    collections = [c[Collection.name] for c in get_collections_in_root(session, root_collection)]
    collection_number = 1

    def _add_up(d: Dict[str, int], name: str, value: int) -> None:
        if name in d:
            d[name] += value
        else:
            d[name] = value

    for collection in collections:
        if print_progress and (collection_number % 10 == 0 or (len(collections) > 10 and collection_number == len(collections))):
            _print_v(f" Processing data for {collection} - subcollection {collection_number}/{len(collections)} ...")

        dataobjects = (session.query(DataObject.name, DataObject.size, DataObject.replica_number, DataObject.modify_time)
                       .filter(Collection.name == collection)
                       .get_results())

        # Divide replica size across old and new data on a per data object basis
        old_data: Dict[str, int] = dict()
        new_data: Dict[str, int] = dict()
        for d in dataobjects:
            if d[DataObject.modify_time].timestamp() >= cutoff_timestamp:
                _add_up(new_data, d[DataObject.name], d[DataObject.size])
            else:
                _add_up(old_data, d[DataObject.name], d[DataObject.size])

        # Categorize each data object as either having a new replica or not having one
        # and add up replica sizes accordingly:
        dataobject_names = set.union(set(old_data.keys()), set(new_data.keys()))
        for dataobject_name in dataobject_names:
            size_all_replicas = old_data.get(dataobject_name, 0) + new_data.get(dataobject_name, 0)
            results[both_data_label] += size_all_replicas
            if dataobject_name in new_data:
                results[new_data_label] += size_all_replicas
            else:
                results[old_data_label] += size_all_replicas

        collection_number += 1

    return results


def get_cutoff_timestamp(days_ago: int) -> int:
    return int(datetime.now().timestamp() - days_ago * 3600 * 24)


def aggregate_by_category(inputdata: List[Dict[str, Union[str, int]]], environment: Union[str, None]) -> List[Dict[str, Union[str, Union[str, int]]]]:
    data_by_category: Dict[str, Dict[str, Union[str, int]]] = dict()

    def _update_category(category_data: Dict[str, Union[str, int]], rowdata: Dict[str, Union[str, int]]) -> None:
        for k in [k for k in category_data.keys() if "size" in k]:
            # Add via temporary variable to avoid type checking problems
            new_value = int(category_data[k]) + int(rowdata[k])
            category_data[k] = new_value

    def _add_category(category_data: Dict[str, Dict[str, Union[str, int]]], rowdata: Dict[str, Union[str, int]]) -> None:
        category = str(rowdata["Category"])
        category_data[category] = dict()
        for k in [k for k in rowdata.keys() if "size" in k]:
            category_data[category][k] = int(rowdata[k])

    # Calculate data by category
    for rowdata in inputdata:
        if rowdata["Category"] in data_by_category:
            _update_category(data_by_category[str(rowdata["Category"])], rowdata)
        else:
            _add_category(data_by_category, rowdata)

    output = []

    # Return aggregated data in list format
    for category in sorted(data_by_category.keys()):
        category_data = data_by_category[category]
        category_data["Category"] = category
        category_data["Subcategory"] = "all"
        category_data["Group name"] = "all"
        if environment is not None:
            category_data["Environment"] = environment
        output.append(category_data)

    return output


def report_oldvsnewdata(args: argparse.Namespace, session: iRODSSession):
    output = csv.DictWriter(sys.stdout, delimiter=',', fieldnames=_get_columns(args))
    output.writeheader()
    cutoff_timestamp = get_cutoff_timestamp(args.days_ago)
    outputdata = []

    for group in sorted(_get_relevant_groups_list(session)):
        if args.progress:
            _print_v(f"Processing data for group {group} ...")

        group_rowdata = _get_group_rowdata(session, group, args.environment)

        research_coll = _get_research_group_collection(session, group)
        vault_coll = _get_vault_group_collection(session, group)
        revisions_coll = _get_revision_group_collection(session, group)

        research_coll_data = get_collection_data(session,
                                                 research_coll,
                                                 cutoff_timestamp,
                                                 "Research collection size",
                                                 args.progress)
        vault_coll_data = get_collection_data(session,
                                              vault_coll,
                                              cutoff_timestamp,
                                              "Vault collection size",
                                              args.progress)
        revisions_coll_data = get_collection_data(session,
                                                  revisions_coll,
                                                  cutoff_timestamp,
                                                  "Revisions size",
                                                  args.progress)

        total_coll_data = dict()
        total_coll_data["Total size (old data)"] = (research_coll_data["Research collection size (old data)"]
                                                    + vault_coll_data["Vault collection size (old data)"]
                                                    + revisions_coll_data["Revisions size (old data)"])
        total_coll_data["Total size (new data)"] = (research_coll_data["Research collection size (new data)"]
                                                    + vault_coll_data["Vault collection size (new data)"]
                                                    + revisions_coll_data["Revisions size (new data)"])
        total_coll_data["Total size (both)"] = total_coll_data["Total size (old data)"]  + total_coll_data["Total size (new data)"]

        rowdata = {**group_rowdata, **research_coll_data, **vault_coll_data, **revisions_coll_data, **total_coll_data}

        # Convert sizes to human-readable format if needed
        for column in rowdata.keys():
            if "size" in column:
                rowdata[column] = _size_to_str(rowdata[column], args.human_readable)

        outputdata.append(rowdata)

    if args.aggregate_by_category:
        outputdata = aggregate_by_category(outputdata, args.environment)

    for rowdata in outputdata:
        output.writerow(rowdata)
