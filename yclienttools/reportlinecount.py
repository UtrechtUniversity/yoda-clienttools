'''Shows a report of the line counts of data objects.'''
  
import argparse
import csv
import sys
from irods.models import Collection, DataObject
from yclienttools import common_args, common_config, common_queries
from yclienttools import session as s


def entry():
    '''Entry point'''
    try:
        args = _get_args()
        yoda_version =  args.yoda_version if args.yoda_version is not None else common_config.get_default_yoda_version()
        output = csv.writer(sys.stdout, delimiter=',')
        session = s.setup_session(yoda_version)

        if args.collection: 
            if not common_queries.collection_exists(session, args.collection):
                print ("Error: collection {} does not exist (or you don't have access)".format(args.collection),
                    file=sys.stderr)
                sys.exit(1)

            print_objectsincollection(session, output, args.collection)

        elif args.data_object:
            if not common_queries.dataobject_exists(session, args.data_object):
                print ("Error: data object {} does not exist (or you don't have access)".format(args.data_object),
                    file=sys.stderr)
                sys.exit(1)
            
            print_singleobject(session, output, args.data_object)

        session.cleanup()

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)


def _get_args():
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description=__doc__)
    common_args.add_default_args(parser)
    fileorcollection = parser.add_mutually_exclusive_group(required=True)
    fileorcollection.add_argument("-c", "--collection", default=None,
                        help='show line counts of all data objects in this collection (recursive)')
    fileorcollection.add_argument("-d", "--data-object", default=None,
                        help='show line count of only this data object')
    return parser.parse_args()

def print_singleobject(session, output, data_object):
    '''Print line count of single data object'''
    fd = session.data_objects.get(data_object).open()
    linecount = sum ( [ 1 for line in fd ] )
    output.writerow([data_object, str(linecount)])

def print_objectsincollection(session, output, collection):
    '''Print line count of all data objects in a collection (as well as its subcollections)'''
    for dataobject in common_queries.get_dataobjects_in_collection(session, collection):
        print_singleobject(session, output, dataobject)

