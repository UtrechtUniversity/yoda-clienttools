#!/usr/bin/env python3

# Depth-first irm: recursively removes a collection tree, starting at the leafs.
# Main use case: removing collection trees that are too big to remove with irm in one go
# (because of memory usage).

import argparse
import sys

from yclienttools.common_args import add_default_args
from yclienttools.common_config import get_default_yoda_version
from yclienttools.common_file_ops import remove_collection_data
from yclienttools.common_queries import collection_exists
from yclienttools.session import setup_session


def parse_args():
    parser = argparse.ArgumentParser(description='ydf_irm: recursively remove collection trees on iRODS (depth-first)')
    add_default_args(parser)
    parser.add_argument("collection", help="Collection to remove (absolute path)")
    parser.add_argument("-v", "--verbose", help="Verbose mode for printing debug information",
                        action="store_true", default=False)
    parser.add_argument("-c", "--continue-failure", help="Continue if an error occurs while removing data",
                        action="store_true", default=False)
    parser.add_argument("-d", "--dry-run", help="Dry run mode - does not actually delete collection", action="store_true", default=False)
    parser.add_argument("-m", "--min-depth", help="Minimum depth of tree to remove (default: 3)", type=int, default=3)
    parser.add_argument("-k", "--keep-collection-itself",
                        help="Only remove subcollections from this collection. Keep collection itself.")
    return parser.parse_args()


def _contains_dotdot(path):
    return path.startswith("../") or path.endswith("/..") or "/../" in path


def _is_absolute(path):
    return path.startswith("/")


def _get_depth(path):
    count = 0
    for char in path.lstrip("/").rstrip("/"):
        if char == "/":
            count += 1
    return count


def sanity_check_args(args):
    if not _is_absolute(args.collection):
        _exit_with_error("Error: collection path must be absolute, for safety reasons.")
    if _contains_dotdot(args.collection):
        _exit_with_error("Error: collection path must not contain .., for safety reasons.")
    if _get_depth(args.collection) < args.min_depth:
        _exit_with_error("Error: collection depth is less than minimum depth set for safety reasons. "
                         + "Reduce minimum depth if you are sure you want to remove this collection.")


def _exit_with_error(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def entry():
    try:
        main()
    except KeyboardInterrupt:
        print('Script stopped by user.', file=sys.stderr)


def main():
    args = parse_args()
    yoda_version = args.yoda_version if args.yoda_version is not None else get_default_yoda_version()
    sanity_check_args(args)
    session = setup_session(yoda_version)
    if not collection_exists(session, args.collection):
        _exit_with_error("Error: collection does not exist.")
    remove_collection_data(args.collection,
                           args.verbose,
                           args.dry_run,
                           args.continue_failure,
                           not args.keep_collection_itself)
