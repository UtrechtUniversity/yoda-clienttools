from itertools import chain
from irods.column import Like
from irods.models import Collection

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

