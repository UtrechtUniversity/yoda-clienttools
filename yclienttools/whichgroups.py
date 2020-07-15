'''Returns a list of groups of which a user is a member'''

import argparse
import sys
from irods.models import User, UserGroup
from yclienttools import common_queries
from yclienttools import session as s


def entry():
    '''Entry point'''
    try:
        args = _get_args()
        session = s.setup_session()

        if not common_queries.user_exists(session, args.username):
            print("Error: user {} does not exist.".format(args.username),
                  file=sys.stderr)
            session.cleanup()
            sys.exit(1)

        groups = session.query(
            UserGroup.name).filter(
                User.name == args.username).get_results()

        for group in sorted(list(map(lambda g: g[UserGroup.name], groups))):
            print(group)

        session.cleanup()

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)


def _get_args():
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username", help='The username')
    return parser.parse_args()
