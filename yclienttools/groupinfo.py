'''Shows information about a Yoda research group'''

import argparse
import sys 
from irods.models import UserGroup, UserMeta
from yclienttools import common_queries
from yclienttools import session as s


def entry():
    '''Entry point'''
    try:
        args = _get_args()
        session = s.setup_session(args,
            require_ssl = False if args.yoda_version == "1.7" else True)


        if not common_queries.group_exists(session,args.groupname):
            _exit_with_error(session, "Group does not exist")
        elif not (args.groupname.startswith("research-")):
            _exit_with_error(session, "This iRODS group is not a Yoda research group")

        print("Category: {}".format(
            _get_group_metadata_single(session, args.groupname, 'category')))
        print("Subcategory: {}".format(
            _get_group_metadata_single(session, args.groupname, 'subcategory')))

        session.cleanup()

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)


def _get_args():
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("groupname")
    parser.add_argument("-y", "--yoda-version", default ="1.7", choices = ["1.7", "1.8"],
                        help="Yoda version on the server (default: 1.7)")
    return parser.parse_args()

def _exit_with_error(session, message):
    print("Error: {}".format(message), file=sys.stderr)
    session.cleanup()
    sys.exit(1)

def _get_group_metadata_single(session, groupname, attributename):
    meta = list(session.query(UserMeta.value).filter(
        UserGroup.name == groupname).filter(
        UserMeta.name == attributename).get_results())
    if len(meta) == 0:
        raise Exception("Attribute {} not found".format(attributename))
    elif len(meta) > 1:
        raise Exception("Attribute {} has multiple values".format(attributename))
    else:
        return meta[0][UserMeta.value]     
