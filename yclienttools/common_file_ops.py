"""This file contains common functions for processing data objects and collections"""

import subprocess
import sys

""" Removes data (collections and data objects) from a collection

    :param collection: collection name
    :param verbose: whether to print additional progress messages
    :param dry_run: whether to only show what collections would be removed, but not actually remove them
    :param continue_failure: continue if irm returns a failure code
    :param remove_coll_itself: whether to remove the collection itself too
"""


def remove_collection_data(collection, verbose, dry_run, continue_failure, remove_coll_itself):
    collection_tree = _get_subcollections_by_depth(collection)
    _remove_leaf_to_stem(collection_tree, collection, dry_run, verbose, continue_failure, remove_coll_itself)


def _remove_leaf_to_stem(collections, stempath, dry_run, verbose, continue_failure, remove_coll_itself):
    stem_depth = _get_depth(stempath)
    depths = sorted(collections.keys())
    depths.reverse()

    for object in _get_dataobjects_in_coll(stempath):
        if dry_run:
            _print_v("Dry run - would remove data object {} ...".format(object))
        else:
            if verbose:
                _print_v("Removing data object {} ...".format(object))
            _irm_do(object, continue_failure)

    for depth in depths:
        if depth == stem_depth and not remove_coll_itself:
            continue
        assert (depth >= stem_depth)
        if verbose:
            _print_v("Processing collections at depth {} ...".format(str(depth)))
        for coll in sorted(collections[depth]):
            assert (coll.startswith(stempath + "/") or coll == stempath)
            if dry_run:
                _print_v("Dry run - would remove collection {} ...".format(coll))
            else:
                if verbose:
                    _print_v("Removing collection {} ...".format(coll))
                _irm_coll(coll, continue_failure)


def _exit_with_error(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def _print_v(message):
    print(message, file=sys.stderr)


def _irm_coll(path, continue_failure):
    result = subprocess.Popen(["irm", "-r", path])
    returncode = result.wait()
    if returncode != 0:
        message = "Error: irm command for collection {} failed.".format(path)
        if continue_failure:
            _print_v(message)
        else:
            _exit_with_error(message)


def _irm_do(path, continue_failure):
    result = subprocess.Popen(["irm", path])
    returncode = result.wait()
    if returncode != 0:
        message = "Error: irm command for data object {} failed.".format(path)
        if continue_failure:
            _print_v(message)
        else:
            _exit_with_error(message)


def _get_cmd_stdout_lines(args):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode('UTF-8').split('\n')


def _get_subcollections_by_depth(path):
    collections = {_get_depth(path): {path: 1}}
    query_command = ["iquest", "--no-page", "%s",
                     "SELECT COLL_NAME WHERE COLL_NAME LIKE '{}/%'.".format(path)]

    for line in _get_cmd_stdout_lines(query_command):
        if line.startswith(path + "/"):
            depth = _get_depth(line)
            if depth in collections:
                collections[depth][line] = 1
            else:
                collections[depth] = {line: 1}

    return collections


def _get_dataobjects_in_coll(coll):
    result = []
    query_command = ["iquest", "--no-page", "%s/%s",
                     "SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = '{}'".format(coll)]

    for line in _get_cmd_stdout_lines(query_command):
        if line.startswith(coll + "/"):
            result.append(line.strip())

    return result


def _get_depth(path):
    count = 0
    for char in path.lstrip("/").rstrip("/"):
        if char == "/":
            count += 1
    return count
