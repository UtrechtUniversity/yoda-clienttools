'''Generates a report of the contents of an intake collection.'''

import argparse
import humanize
import sys
import time
from collections import OrderedDict, defaultdict
from irods.models import Collection
from yclienttools import common_queries
from yclienttools.options import GroupByOption
from yclienttools.session import setup_session


def _get_args():
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-p', '--progress', action='store_true',
                        help='Show progress updates.')
    parser.add_argument('-s', '--study', required=True,
                        help='Study to process')
    return parser.parse_args()


def entry():
    try:
        main()
    except KeyboardInterrupt:
        print('Script stopped by user.', file=sys.stderr)


def main():
    args = _get_args()
    session = setup_session()
    vault_collection = _get_vault_collection(session, args.study)
    if not common_queries.collection_exists(session, vault_collection):
        print("Error: no vault collection {} found for study {}.".format(
            vault_collection, args.study), file=sys.stderr)
        sys.exit(1)
    vault_dataset_count = _get_vault_dataset_count(session, vault_collection, args.progress)
    aggregated_dataset_info = _get_aggregated_dataset_info(
        session, vault_collection, args.progress)
    for category in ["raw", "processed"]:
        _print_vault_dataset_count(vault_dataset_count, category)
    for category in ["raw", "processed", "total"]:
        _print_aggregated_dataset_info(aggregated_dataset_info, category)


def _get_subcollections(session, collection):
    return session.query(Collection.name)


def _get_datasets_with_metadata(session, root):
    '''Return a nested dictionary of subcollections in a root collection and their intake module metadata. Keys of the outer
       dictionary are names of subcollections. The inner dictionaries contains the intake module metadata of each subcollection, with
       the metadata field names in the keys. Only subcollections that have at least one intake module metadata field are present in the output.'''
    datasets = defaultdict(lambda: defaultdict(dict))

    for collection in common_queries.get_collections_in_root(session, root):
        collection_name = collection[Collection.name]
        metadata_collection = session.collections.get(collection_name).metadata
        for metadata in metadata_collection.items():
            if metadata.name in ["version", "experiment_type"]:
                metadata.value = metadata.value.lower()
            if metadata.name in ["dataset_date_created", "wave",
                                 "version", "experiment_type", "pseudocode"]:
                datasets[collection_name][metadata.name] = metadata.value

    return datasets


def _get_vault_dataset_count(session, intakecollection, progress):
    '''Returns a nested dictionary with counts of datasets per experiment type, wave and version in an intake
       folder.'''
    counts = defaultdict(lambda: defaultdict(dict))

    if progress:
        _print_progress_update("Retrieving list of of datasets and their metadata ...")

    for collection, metadata in _get_datasets_with_metadata(
            session, intakecollection).items():
        if "dataset_date_created" in metadata:
            et = metadata['experiment_type']
            wave = metadata['wave']
            version = metadata['version']
            if version in counts[et][wave]:
                counts[et][wave][version] += 1
            else:
                counts[et][wave][version] = 1

    if progress:
        _print_progress_update("Counting datasets in vault finished.")

    return counts


def _get_aggregated_dataset_info(session, intakecollection, progress):
    '''Returns a nested dictionary with three dictionaries containing aggregated data of all raw datasets, all processed
       datasets, as well as of overall (total) statistics.'''

    if progress:
        _print_progress_update("Starting collection of aggregated dataset information ...")

    results = defaultdict(lambda: defaultdict(dict))
    for category in ["raw", "processed"]:
        for variable in ["dataset_count", "dataset_growth",
                         "file_count", "total_filesize", "filesize_growth"]:
            results[category][variable] = 0

    ref_lastmonth = time.time() - 30 * 24 * 3600

    for collection, metadata in _get_datasets_with_metadata(
            session, intakecollection).items():
        if "dataset_date_created" not in metadata:
            # Collection is only considered a dataset if it has the
            # dataset_date_created field
            continue

        if progress:
            _print_progress_update("Collecting statistics for collection {} ...".format(collection))

        if metadata["version"] == "raw":
            category = "raw"
        else:
            category = "processed"

        results[category]["dataset_count"] += 1

        file_count = common_queries.get_dataobject_count(session, collection)
        results[category]["file_count"] += file_count

        filesize_dict = common_queries.get_collection_size(
            session, collection, False, GroupByOption.none, False)
        total_filesize = filesize_dict["all"]
        results[category]["total_filesize"] += total_filesize

        pseudocode = metadata["pseudocode"]
        results[category]["pseudocodes"][pseudocode] = True

        if int(metadata["dataset_date_created"]) > ref_lastmonth:
            results[category]["dataset_growth"] += 1
            results[category]["filesize_growth"] += total_filesize

    for category, stats in results.items():
        stats['pseudocode_count'] = len(stats["pseudocodes"].keys())
        stats.pop("pseudocodes")

    for variable, value in results['raw'].items():
        results["total"][variable] = results["raw"][variable] + \
            results["processed"][variable]

    if progress:
        _print_progress_update("Finished collection of aggregated dataset information.")

    return results


def _get_vault_collection(session, study):
    return "/{}/home/grp-vault-{}".format(session.zone, study)

def _print_progress_update(message):
    print("Progress: {}".format(message), file=sys.stderr)

def _print_vault_dataset_count(vault_dataset_count, category):
    print()
    print("Vault count statistics for category {}".format(category.title()))
    print()

    if category == "raw":
        print("{:20}{:10}{:10}".format("Type", "Wave", "Count"))
        print("-" * 40)
    else:
        print("{:20}{:20}{:10}{:10}".format("Type", "Version", "Wave", "Count"))
        print("-" * 60)

    for et in sorted(vault_dataset_count.keys()):
        et_data = vault_dataset_count[et]
        for wave in sorted(et_data.keys()):
            wave_data = et_data[wave]
            for version in sorted(wave_data.keys()):
                count = wave_data[version]
                if category == "raw" and version == "raw":
                    print("{:20}{:10}{:10}".format(et, wave, count))
                elif category == "raw":
                    pass
                elif category == "processed" and version != "raw":
                    print(
                        "{:20}{:20}{:10}{:10}".format(
                            et, version, wave, count))
                elif category == "processed":
                    pass
                else:
                    print(
                        "Warning: unexpected category / version combination {} / {}".format(
                            category, version), file=sys.stderr)
                    sys.exit(1)


def _print_aggregated_dataset_info(dataset_info, category):
    print()
    print("Aggregated dataset statistics for category {}".format(category.title()))
    print()

    labels = OrderedDict([
        ("dataset_count", "Total datasets"),
        ("file_count", "Total files"),
        ("total_filesize", "Total file size"),
        ("filesize_growth", "File size growth last month"),
        ("dataset_growth", "New datasets last month"),
        ("pseudocode_count", "Number of pseudocodes"),
    ])

    for variable, label in labels.items():
        raw_value = dataset_info[category][variable]
        if variable in ["total_filesize", "filesize_growth"]:
            value = str(humanize.naturalsize(raw_value))
        else:
            value = str(raw_value)
        print("{:30}{:10}".format(label, value))
