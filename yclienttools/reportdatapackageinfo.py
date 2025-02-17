import argparse
import sys
import csv
import humanize
from urllib.parse import urlparse
from irods.models import Collection, CollectionMeta
from yclienttools import common_args, common_config, common_queries
from yclienttools import session as s
from yclienttools.options import GroupByOption


def entry():
    '''Entry point'''
    try:
        args = _get_args()
        yoda_version = args.yoda_version if args.yoda_version is not None else common_config.get_default_yoda_version()
        session = s.setup_session(yoda_version)

        data_package_report(args, session)
        session.cleanup()

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)


def _get_args():
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    common_args.add_default_args(parser)
    parser.add_argument('--help', action='help', help='show help information')
    parser.add_argument('-h', '--human-readable', action='store_true', default=False,
                        help="Show sizes in human readable format, e.g. 1.0MB instead of 1000000")
    return parser.parse_args()


def data_package_report(args, session):
    output = csv.writer(sys.stdout, delimiter=',')
    output.writerow(["Path", "Size", "Publication status", "Publication date", "Has README file", "License type", "Data access type", "Metadata schema"])

    for data_package in common_queries.get_vault_data_packages(session):
        _get_package_info(output, session, data_package, args.human_readable)


def _get_package_info(csv_output, session, collection, human_readable):
    raw_size = common_queries.get_collection_size(session, collection, True, GroupByOption.none, False)['all']
    vault_status = _get_vault_status(session, collection)
    publication_date = _get_publication_date(session, collection)
    has_readme = _has_readme_file(session, collection)
    license_type = _get_license(session, collection)
    data_access = _get_data_access(session, collection)
    metadata_schema = _get_metadata_schema(session, collection)

    if human_readable:
        display_size = str(humanize.naturalsize(raw_size))
    else:
        display_size = str(raw_size)

    csv_output.writerow([collection, display_size, vault_status, publication_date, has_readme, license_type, data_access, metadata_schema])


def _get_vault_status(session, collection):
    """Returns vault status of data package (or None if not found)."""
    query_results = list(session.query(CollectionMeta.value).filter(
        Collection.name == collection).filter(
        CollectionMeta.name == 'org_vault_status').get_results())

    if len(query_results) == 1:
        return query_results[0][CollectionMeta.value]

    return None


def _get_publication_date(session, collection):
    """Returns publication date of data package (or None if not found)."""
    query_results = list(session.query(CollectionMeta.value).filter(
        Collection.name == collection).filter(
        CollectionMeta.name == 'org_publication_publicationDate').get_results())

    if len(query_results) == 1:
        return query_results[0][CollectionMeta.value]

    return None


def _has_readme_file(session, collection):
    """Returns True if data package contains a README file, otherwise False."""
    for data_obj in common_queries.get_dataobjects_in_collection(session, collection):
        if "readme" in data_obj.lower():
            return True

    return False


def _get_license(session, collection):
    """Returns license of data package (or None if not found)."""
    query_results = list(session.query(CollectionMeta.value).filter(
        Collection.name == collection).filter(
        CollectionMeta.name == 'License').get_results())

    if len(query_results) == 1:
        return query_results[0][CollectionMeta.value]

    return None


def _get_data_access(session, collection):
    """Returns data access type of data package (or None if not found)."""
    query_results = list(session.query(CollectionMeta.value).filter(
        Collection.name == collection).filter(
        CollectionMeta.name == 'Data_Access_Restriction').get_results())

    if len(query_results) == 1:
        return query_results[0][CollectionMeta.value]

    return None


def _get_metadata_schema(session, collection):
    """Returns metadata schema of data package (or None if not found)."""
    query_results = list(session.query(CollectionMeta.value).filter(
        Collection.name == collection).filter(
        CollectionMeta.name == 'href').get_results())

    if len(query_results) == 1:
        href = query_results[0][CollectionMeta.value]
        href_parts = urlparse(href).path.split('/')
        return href_parts[-2]

    return None
