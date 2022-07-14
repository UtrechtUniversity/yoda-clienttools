'''Searches for groups by a search string'''

import argparse
import sys
from irods.column import Like
from irods.models import UserGroup
from yclienttools import common_queries
from yclienttools import session as s


def entry():
    '''Entry point'''
    try:
        args = _get_args()
        session = s.setup_session(args,
            require_ssl = False if args.yoda_version == "1.7" else True)

        groups = session.query(UserGroup.name).filter(
            Like(UserGroup.name, "%{}%".format(args.searchstring))).get_results()
        for group in sorted(list(map(lambda g: g[UserGroup.name], groups))):
            if ( args.all or
                    group.startswith("research-") or
                    group.startswith("vault-") ):
                print(group)

        session.cleanup()

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)


def _get_args():
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("searchstring", help='The string to search for')
    parser.add_argument("-y", "--yoda-version", default ="1.7", choices = ["1.7", "1.8"],
                        help="Yoda version on the server (default: 1.7)")
    parser.add_argument("-a", "--all", 
            help='Show all groups (not just research and vault groups)',
            action='store_true')
    return parser.parse_args()
