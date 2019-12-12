# Yoda-clienttools

Client-side Yoda tools - mainly intended for data managers and key users

## Overview of tools

### yreport\_collectionsize

Shows a report of the size of all data objects in a collection and its subcollections

```
usage: yreport_collectionsize [-h] -c COLLECTION

optional arguments:
  --help                show help information
  -c COLLECTION, --collection COLLECTION
                        Show total size of data objects in this collection and
                        its subcollections
  -h, --all-collections-in-home
                        Show total size of data objects in each collection in
                        /zoneName/home, including its subcollections.
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
