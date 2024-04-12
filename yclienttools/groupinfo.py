'''Shows information about a Yoda research group'''

import argparse
import sys
from irods.models import UserGroup, UserMeta
from yclienttools import common_args, common_config, common_queries
from yclienttools import session as s


def entry():
    '''Entry point'''
    try:
        args = _get_args()
        yoda_version = args.yoda_version if args.yoda_version is not None else common_config.get_default_yoda_version()
        session = s.setup_session(yoda_version)

        if not common_queries.group_exists(session, args.groupname):
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
    common_args.add_default_args(parser)
    parser.add_argument("groupname")
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
