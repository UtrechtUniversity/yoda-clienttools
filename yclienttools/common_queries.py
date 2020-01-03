from itertools import chain
from irods.column import Like
from irods.models import Collection, DataObject, Resource
from yclienttools.options import GroupByOption
from yclienttools import exceptions

def get_collections_in_root(session, root):
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
                                .filter(Like(Collection.name, searchstring ))
                                .get_results()
                                )
    return chain(generator_collection, generator_subcollections)

def get_collection_size(session, collection_name,
                         count_all_replicas, group_by, include_revisions):
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

    result = {}

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


def collection_exists(session, collection):
    '''Returns a boolean value that indicates whether a collection with the provided name exists.'''
    return len(list(session.query(Collection.name).filter(
        Collection.name == collection).get_results())) > 0
