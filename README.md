# Yoda-clienttools

Client-side Yoda tools - mainly intended for data managers and key users

## Overview of tools

### ycleanup\_files

```
usage: ycleanup_files [-h] -r ROOT

Recursively finds data objects in a collection that will typically have to be
cleaned up when a dataset is archived, and deletes them.

optional arguments:
  -h, --help            show this help message and exit
  -r ROOT, --root ROOT  Delete unwanted files in this collection, as well as
                        its subcollections

```

Overview of files to be removed:

| file      | meaning                        |   |   |   |
|-----------|--------------------------------|---|---|---|
| .\_*      | MacOS resource fork            |   |   |   |
| .DS_Store | MacOS custom folder attributes |   |   |   |
| Thumbs.db | Windows thumbnail data         |   |   |   |

### ygrepgroups

```
usage: ygrepgroups [-h] [-a] searchstring

Searches for groups by a search string

positional arguments:
  searchstring  The string to search for

optional arguments:
  -h, --help    show this help message and exit
  -a, --all     Show all groups (not just research and vault groups)
```

### ygroupinfo

Prints the category and subcategory of a Yoda research group.

```
usage: ygroupinfo [-h] groupname

Shows information about a Yoda group

positional arguments:
  groupname

optional arguments:
  -h, --help  show this help message and exit
```

### yimportgroups

```
usage: yimportgroups [-h] -i INTERNAL_DOMAINS
                     [--offline-check | --online-check] [--allow-update]
                     [--verbose]
                     csvfile

Creates a list of groups based on a CSV file

positional arguments:
  csvfile               Name of the CSV file

optional arguments:
  -h, --help            show this help message and exit
  -i INTERNAL_DOMAINS, --internal-domains INTERNAL_DOMAINS
                        Comma-separated list of internal email domains to the Yoda server
  --offline-check, -c   Check mode (offline): verify CSV format only. Does not connect to iRODS and does not create groups
  --online-check, -C    Check mode (online): verify CSV format and that groups do not exist. Does not create groups.
  --allow-update, -u    Allows existing groups to be updated
  --verbose, -v         Show information as extracted from CSV file

        The CSV file is expected to include the following labels in its header (the first row):
        'category'    = category for the group
        'subcategory' = subcategory for the group
        'groupname'   = name of the group (without the "research-" prefix)

        The remainder of the columns should have a label that starts with a prefix which
        indicates the role of each group member:

        'manager:'    = user that will be given the role of manager
        'member:'     = user that will be given the role of member with read/write
        'viewer:'     = user that will be given the role of viewer with read

        Notes:
        - Columns may appear in any order
        - Empty data cells are ignored: groups can differ in number of members

        Example:
        category,subcategory,groupname,manager:manager,member:member1,member:member2
        departmentx,teama,groupteama,m.manager@example.com,m.member@example.com,n.member@example.com
        departmentx,teamb,groupteamb,m.manager@example.com,p.member@example.com,
```

### yreport\_collectionsize

Shows a report of the size of all data objects in a (set of) collections.

```
usage: yreport_collectionsize [--help] [-h] [-r] [-R] [-g GROUP_BY]
                              (-c COLLECTION | -H | -C COMMUNITY)

optional arguments:
  --help                show help information
  -h, --human-readable  Show sizes in human readable format, e.g. 1.0MB
                        instead of 1000000
  -r, --count-all-replicas
                        Count the size of all replicas of a data object. By
                        default, only the size of one replica of each data
                        object is counted.
  -R, --include-revisions
                        Include the size of stored revisions of data objects
                        in the collection (if available).
  -g GROUP_BY, --group-by GROUP_BY
                        Group collection sizes by resource or by location.
                        Argument should be 'none' (the default), 'resource' or
                        'location'. Grouping by resource or location implies
                        --count-all-replicas. If a collection has no
                        dataobjects and --group-by resource / location is
                        enabled, its size will be printed with group 'all'.
  -c COLLECTION, --collection COLLECTION
                        Show total size of data objects in this collection and
                        its subcollections
  -H, --all-collections-in-home
                        Show total size of data objects in each collection in
                        /zoneName/home, including its subcollections. Note:
                        you will only see the collections you have access to.
  -C COMMUNITY, --community COMMUNITY
                        Show total size of data objects in each research and
                        vault collection in a Yoda community. Note: you will
                        only see the collections you have access to.
```

### yreport\_dataobjectspercollection

Prints a report of the number of subcollections and data objects
per collection. The output is in CSV format.

```
usage: yreport_dataobjectspercollection [-h] [-r ROOT] [-e]

Shows a report of number of data objects and subcollections per collection

optional arguments:
  -h, --help            show this help message and exit
  -r ROOT, --root ROOT  show only collections in this root collection
                        (default: show all collections
  -e, --by-extension    show number of data objects by extension for each
                        collection
```

List of columns in regular mode:
1. Number of subcollections in collection (nonrecursive).
2. Number of data objects in collection (nonrecursive).
3. Total number of subcollections and data objects in collection (nonrecursive)
4. Name of collection

List of columns if --by-extension is enabled:
1. Number of subcollections in collection (nonrecursive).
2. Number of data objects in collection with the listed extension (nonrecursive).
3. Total number of subcollections and data objects with the listed extension
   in collection (nonrecursive)
4. Extension
5. Name of collection

### yreport\_intake

Prints an intake collection report. This report is only relevant for environments
that use the intake module.

On systems with a significant number of datasets, it is recommended to use the
--cache parameter to keep a local cache of dataset statistics in order to speed
up report generation.

```

usage: yreport_intake [-h] [-p] -s STUDY [-c CACHE]

Generates a report of the contents of an intake collection.

optional arguments:
  -h, --help            show this help message and exit
  -p, --progress        Show progress updates.
  -s STUDY, --study STUDY
                        Study to process
  -c CACHE, --cache CACHE
                        Local cache directory. Can be used to retrieve
                        previously collected information on datasets, in order
                        to speed up report generation. The script will also
                        store newly collected dataset information in the cache.

```

### yreport\_linecount

Prints a report of the number of lines per data object.

```
usage: yreport_linecount [-h] (-c COLLECTION | -d DATA_OBJECT)

Shows a report of the line counts of data objects.

optional arguments:
  -h, --help            show this help message and exit
  -c COLLECTION, --collection COLLECTION
                        show line counts of all data objects in this
                        collection (recursive)
  -d DATA_OBJECT, --data-object DATA_OBJECT
                        show line count of only this data object
```

### ywhichgroups

Prints a list of all groups a user is a member of.

```
usage: ywhichgroups [-h] username

Returns a list of groups of which a user is a member

positional arguments:
  username    The username

optional arguments:
  -h, --help  show this help message and exit
```

## Installation

The Yoda clienttools require Python 3. They have been tested with Python 3.6.

It is recommended to install the tools in a virtual environment, like this:

```
virtualenv --python /usr/bin/python3.6 --no-site-packages venv
source venv/bin/activate
pip3 install --upgrade git+https://github.com/UtrechtUniversity/yoda-clienttools.git
```

If your zone has data objects or collections with nonstandard characters, you should probably use
a version of python-irodsclient that has a fix for known issues when dealing with such objects:

```
pip3 install --upgrade git+https://github.com/cjsmeele/python-irodsclient@xml-compatibility
```
