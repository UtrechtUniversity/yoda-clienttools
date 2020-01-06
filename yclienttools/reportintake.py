'''Generates a report of the contents of an intake collection.'''

import argparse
import csv
from glob import glob
import humanize
import os
import sys
from time import time
from collections import OrderedDict, defaultdict
from irods.models import Collection
from yclienttools import common_queries
from yclienttools.options import GroupByOption
from yclienttools.session import setup_session


class DatasetStatisticsCache:
    '''This object stores statistics of a dataset in files in a local cache directory.'''

    def __init__(self, dir):
        self.dir = dir
        self.memstore = {}
        self.load()

    def load(self):
        '''Load statistics from the on-disk cache directory into the cache.'''
        self.filestore = {}
        for filename in glob(os.path.join(self.dir, "dsscache.*.dat")):
            with open(filename) as cache_file:
                for line in csv.reader(cache_file):
                    data = {"num": int(line[1]), "size": int(line[2])}
                    self.filestore[line[0]] = data

    def save(self):
        '''Store statistics that have been added to the cache using the put function on disk in the cache directory.'''
        if len(self.memstore.keys()) == 0:
            return

        filename = os.path.join(self.dir, "dsscache.{}.dat".format(time()))

        with open(filename, "w") as cache_file:
            writer = csv.writer(cache_file)
            for path, data in self.memstore.items():
                writer.writerow([path, str(data["num"]), str(data["size"])])
                self.filestore[path] = data

        self.memstore = {}

    def get(self, pathname):
        '''Fetch statistics of a dataset from cache.'''
        if pathname in self.filestore:
            return self.filestore[pathname]
        elif pathname in self.memstore:
            return self.memstore[pathname]
        else:
            return None

    def has(self, pathname):
        '''Returns boolean value that says whether the cache has an entry for this dataset.'''
        return pathname in self.filestore or pathname in self.memstore

    def put(self, pathname, num_objects, total_size):
        '''Put statistics of a dataset in the cache.'''
        self.memstore[pathname] = {"num": num_objects, "size": total_size}


def _get_args():
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-p', '--progress', action='store_true',
                        help='Show progress updates.')
    parser.add_argument('-s', '--study', required=True,
                        help='Study to process')
    parser.add_argument('-c', '--cache', default=None,
                        help='Local cache directory. Can be used to retrieve previously collected information on datasets, in order to speed up report generation. The script will also store newly collected dataset information in the cache.')

    args = parser.parse_args()

    if args.cache is not None and not os.path.isdir(args.cache):
        print(
            "Error: cache argument is not a valid directory.",
            file=sys.stderr)
        sys.exit(1)

    return args


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

    if args.cache:
        if args.progress:
            _print_progress_update("Loading dataset statistics cache ...")
        cache = DatasetStatisticsCache(args.cache)
    else:
        cache = None

    if args.progress:
        _print_progress_update("Compiling list of datasets in vault ...")
    datasets = _get_datasets_with_metadata(session, vault_collection).items()
    if args.progress:
        _print_progress_update("Compiling list of datasets in vault finished.")

    vault_dataset_count = _get_vault_dataset_count(
        session, datasets, vault_collection, args.progress)
    aggregated_dataset_info = _get_aggregated_dataset_info(
        session, datasets, vault_collection, args.progress, cache)

    for category in ["raw", "processed"]:
        _print_vault_dataset_count(vault_dataset_count, category)
    for category in ["raw", "processed", "total"]:
        _print_aggregated_dataset_info(aggregated_dataset_info, category)

    if args.cache:
        cache.save()


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


def _get_vault_dataset_count(session, datasets, intakecollection, progress):
    '''Returns a nested dictionary with counts of datasets per experiment type, wave and version in an intake
       folder.'''
    counts = defaultdict(lambda: defaultdict(dict))

    if progress:
        _print_progress_update(
            "Counting number of datasets in vault ...")

    for collection, metadata in datasets:
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


def _get_aggregated_dataset_info(
        session, datasets, intakecollection, progress, cache):
    '''Returns a nested dictionary with three dictionaries containing aggregated data of all raw datasets, all processed
       datasets, as well as of overall (total) statistics.'''

    if progress:
        _print_progress_update(
            "Starting collection of aggregated dataset information ...")

    results = defaultdict(lambda: defaultdict(dict))
    for category in ["raw", "processed"]:
        for variable in ["dataset_count", "dataset_growth",
                         "file_count", "total_filesize", "filesize_growth"]:
            results[category][variable] = 0

    ref_lastmonth = time() - 30 * 24 * 3600

    for collection, metadata in datasets:
        if "dataset_date_created" not in metadata:
            # Collection is only considered a dataset if it has the
            # dataset_date_created field
            continue

        if metadata["version"] == "raw":
            category = "raw"
        else:
            category = "processed"

        results[category]["dataset_count"] += 1

        if cache is not None and cache.has(collection):

            cache_entry = cache.get(collection)
            file_count = cache_entry["num"]
            total_filesize = cache_entry["size"]

            if progress:
                _print_progress_update(
                    "Retrieved statistics of collection {} from cache.".format(collection))
        else:

            if progress:
                _print_progress_update(
                    "Calculating statistics for collection {} ...".format(collection))

            file_count = common_queries.get_dataobject_count(
                session, collection)
            filesize_dict = common_queries.get_collection_size(
                session, collection, False, GroupByOption.none, False)
            total_filesize = filesize_dict["all"]

            if cache is not None:
                cache.put(collection, file_count, total_filesize)

        results[category]["file_count"] += file_count
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
        _print_progress_update(
            "Finished collection of aggregated dataset information.")

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
        print(
            "{:20}{:20}{:10}{:10}".format(
                "Type",
                "Version",
                "Wave",
                "Count"))
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
