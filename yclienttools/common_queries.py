import datetime
import itertools
import os
from itertools import chain
from typing import Dict, Union

from irods.column import Like
from irods.models import Collection, DataObject, Resource, User, UserGroup
from irods.session import iRODSSession
from yclienttools import exceptions
from yclienttools.options import GroupByOption


def get_collections_in_root(session: iRODSSession, root: str) -> itertools.chain:
    '''Get a generator of collections within a root collection, including the root collection itself.'''

    if root.endswith("/"):
        searchstring = "{}%%".format(root)
    else:
        searchstring = "{}/%%".format(root)

    generator_collection = (session.query(Collection.id, Collection.name)
                            .filter(Collection.name == root)
                            .get_results()
                            )
    generator_subcollections = (session.query(Collection.id, Collection.name)
                                .filter(Like(Collection.name, searchstring))
                                .get_results()
                                )
    return chain(generator_collection, generator_subcollections)


def get_collection_size(session: iRODSSession,
                        collection_name: str,
                        count_all_replicas: bool,
                        group_by: GroupByOption,
                        include_revisions: bool) -> Dict[str, int]:
    '''Get total size of all data objects in collection (including its subcollections).
       Options:
       - count_all_replicas (boolean): specifies whether to count the size of each data
         object once (False), or to count the total size of its replicas (True)
       - group_by: (GroupByOption): specifies by what variable to group the total size.
         if count_all_replicas is False, it does not make sense to group by a variable,
         so group_by should be set to GroupByOption.none in that case.
       - include_revisions: specifies whether to include the size of the revision
         collection in the collection size.
    '''

    result: Dict[str, int] = {}

    collections = get_collections_in_root(
        session, collection_name)

    if len(list(collections)) == 0:
        raise exceptions.NotFoundException

    original_collections = get_collections_in_root(
        session, collection_name)
    revision_collection_name = get_revision_collection_name(
        session, collection_name)

    if revision_collection_name is None or not include_revisions:
        all_collections = original_collections
    else:
        revision_collections = get_collections_in_root(
            session, revision_collection_name)
        all_collections = chain(
            original_collections, revision_collections)

    for collection in all_collections:
        if count_all_replicas:
            dataobjects = (session.query(Collection.name, DataObject.name, DataObject.size,
                                         DataObject.path, Resource.name, Resource.location)
                           .filter(Collection.name == collection[Collection.name])
                           .get_results())
        else:
            dataobjects = (session.query(Collection.name, DataObject.name, DataObject.size)
                           .filter(Collection.name == collection[Collection.name])
                           .get_results())
        for dataobject in dataobjects:

            if group_by == GroupByOption.none:
                key = 'all'
            elif group_by == GroupByOption.resource:
                key = dataobject[Resource.name]
            elif group_by == GroupByOption.location:
                key = dataobject[Resource.location]
            else:
                raise Exception("Unknown group_by value {}".format(key))

            if key in result:
                result[key] = result[key] + dataobject[DataObject.size]
            else:
                result[key] = dataobject[DataObject.size]

    if len(result.keys()) == 0:
        result['all'] = 0

    return result


def get_collection_contents_last_modified(session: iRODSSession, collection_name: str) -> Union[None, datetime.datetime]:
    """Returns datetime of last modification of collection or its contents

       :param session:         iRODS session
       :param collection_name: collection name

       :returns: datetime of last modification of the collection or its contents
                 (data objects or subcollections, recursively), or None if no last
                 modified datetime could be determined
    """
    last_timestamp = None

    dataobjects_root = (session.query(DataObject.modify_time)
                        .filter(Collection.name == collection_name)
                        .get_results())
    dataobjects_sub  = (session.query(DataObject.modify_time)
                        .filter(Like(Collection.name, collection_name + "/%"))
                        .get_results())
    collection_root  = (session.query(Collection.modify_time)
                        .filter(Collection.name == collection_name)
                        .get_results())
    collections_sub  = (session.query(Collection.modify_time)
                        .filter(Like(Collection.name, collection_name + "/%"))
                        .get_results())

    all_collection_data = chain(collection_root, collections_sub)
    all_dataobject_data = chain(dataobjects_root, dataobjects_sub)

    for collection in all_collection_data:
        if last_timestamp is None or collection[Collection.modify_time] > last_timestamp:
            last_timestamp = collection[Collection.modify_time]

    for dataobject in all_dataobject_data:
        if last_timestamp is None or dataobject[DataObject.modify_time] > last_timestamp:
            last_timestamp = dataobject[DataObject.modify_time]

    return last_timestamp


def get_revision_collection_name(session, collection_name):
    '''Returns the revision collection name of a collection if it exists, otherwise None. '''
    expected_prefix = "/{}/home/".format(session.zone)
    if collection_name.startswith(expected_prefix):
        trimmed_collection_name = collection_name.replace(
            expected_prefix, "", 1)
        if "/" in trimmed_collection_name:
            return None
        else:
            revision_collection_name = "/{}/yoda/revisions/{}".format(
                session.zone, trimmed_collection_name)
            if collection_exists(session, revision_collection_name):
                return revision_collection_name
            else:
                return None
    else:
        return None


def get_dataobject_count(session, collection_name):
    '''Returns the number of data objects in a collection (including its subcollections).'''
    return len(get_dataobjects_in_collection(session, collection_name))


def get_dataobjects_in_collection(session, collection_name):
    result = []

    for collection in get_collections_in_root(session, collection_name):
        dataobjects = (session.query(Collection.name, DataObject.name)
                       .filter(Collection.name == collection[Collection.name])
                       .get_results())
        result.extend(map(
            lambda d: "{}/{}".format(d[Collection.name], d[DataObject.name]),
            dataobjects))

    return result


def collection_exists(session, collection):
    '''Returns a boolean value that indicates whether a collection with the provided name exists.'''
    return len(list(session.query(Collection.name).filter(
        Collection.name == collection).get_results())) > 0


def dataobject_exists(session, path):
    '''Returns a boolean value that indicates whether a data object with the provided name exists.'''
    collection_name, dataobject_name = os.path.split(path)
    return len(list(session.query(Collection.name, DataObject.name).filter(
        DataObject.name == dataobject_name).filter(
        Collection.name == collection_name).get_results())) > 0


def user_exists(session, username):
    '''Returns a boolean value that indicates whether a user with the provided name exists.'''
    return len(list(session.query(User.name).filter(User.name == username).get_results())) > 0


def group_exists(session, groupname):
    '''Returns a boolean value that indicates whether a user group with the provided name exists.'''
    return (len(list(session.query(UserGroup.name).filter(
        UserGroup.name == groupname).get_results())) > 0)


def get_vault_data_packages(session):
    """Returns a list of collections of all data packages in the vault space."""
    vault_collections = session.query(Collection.name).filter(
        Collection.parent_name == f'/{session.zone}/home').filter(
        Like(Collection.name, f'/{session.zone}/home/vault-%')).get_results()

    datapackage_collections = []
    for vault_collection in [coll[Collection.name] for coll in vault_collections]:
        these_datapackage_collections = session.query(Collection.name).filter(
            Collection.parent_name == vault_collection).filter(
            Like(Collection.name, f"/{session.zone}/home/vault-%/%[%]")).get_results()
        datapackage_collections.extend([coll[Collection.name] for coll in these_datapackage_collections])

    return datapackage_collections
