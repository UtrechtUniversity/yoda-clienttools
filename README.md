# Yoda-clienttools

Client-side Yoda tools - mainly intended for data managers and key users

## Overview of tools

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
per collection. The output is in CSV format. List of columns:
1. Number of subcollections in collection (nonrecursive).
2. Number of data objects in collection (nonrecursive).
3. Total number of subcollections and data objects in collection (nonrecursive)
4. Name of collection

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
