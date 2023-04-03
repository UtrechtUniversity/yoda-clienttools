# Yoda-clienttools

The Yoda client tools are a set of commandline utilities for Yoda. They are mainly
intended for data managers and key users.

## Installation

The Yoda clienttools require Python 3. They are compatible with Yoda 1.7 and Yoda 1.8.
The tools need to be used with the '-y 1.8' option in order to work with
Yoda 1.8 instances.

It is recommended to install the tools in a virtual environment, like this:

```
/usr/bin/python3.6 -m venv venv
source venv/bin/activate
pip3 install --upgrade git+https://github.com/UtrechtUniversity/yoda-clienttools.git
```

## Installation Windows users

The Yoda clienttools are much easier to use under a Linux environment. For Windows users, please activate Windows Subsystem for Linux and install Ubuntu as described on the Microsoft page https://learn.microsoft.com/en-us/windows/wsl/install. You will also need to install iCommands within your Ubuntu distro as described at https://www.uu.nl/en/research/yoda/guide-to-yoda/i-am-using-yoda/using-icommands-for-large-datasets. You will additionally need to create a .irods folder in your Ubuntu home directory (`mkdir .irods`) and create an irods_environment.json file (`sudo nano irods_environment.json`). The contents of that json file can be found after logging in to the Yoda webportal and clicking on the Yoda version at the bottom of each page in the webportal (e.g., clicking on Yoda v1.8.6 or Yoda v1.9).

Once you have completed the previous steps and have Ubuntu up and running, run the following lines:

```
sudo apt update
sudo apt install python3
sudo apt install python3-pip
sudo apt install python3.8-venv
```

Then create the virtual environment (note that the wheel package is likely not available in the venv under WSL and may require the pip install below):

```
/usr/bin/python3.8 -m venv yodatoolsvenv
source yodatoolsvenv/bin/activate
pip install wheel
pip install --upgrade git+https://github.com/UtrechtUniversity/yoda-clienttools.git

```

Next, the CA certificates locations needs to be set in the session.py file within the Yoda clienttools folder. Within Ubuntu the certificate location is often the location at "/etc/ssl/certs/ca-certificates.crt".

```
cd ~/yodatoolsvenv/lib/python3.8/site-packages/yclienttools
nano session.py
```

With session.py open, adjust the `ca_file = "/etc/irods/localhost_and_chain.crt"` entry to `ca_file = "/etc/ssl/certs/ca-certificates.crt"`. Save the file (ctrl+x en accept) and return to your home folder `cd ~`.

You are now good to go. When you call on the clienttools, make sure you first run `iinit` to sign in to Yoda first. 


## Overview of tools

### ycleanup\_files

```
usage: ycleanup_files [-h] -r ROOT [-y {1.7,1.8,1.9}]

Recursively finds data objects in a collection that will typically have to be
cleaned up when a dataset is archived, and deletes them.

optional arguments:
  -h, --help            show this help message and exit
  -r ROOT, --root ROOT  Delete unwanted files in this collection, as well as
                        its subcollections
  -y {1.7,1.8,1.9}, --yoda-version {1.7,1.8,1.9}
                        Yoda version on the server (default: 1.7)
```

Overview of files to be removed:

| file      | meaning                        |   |   |   |
|-----------|--------------------------------|---|---|---|
| .\_*      | MacOS resource fork            |   |   |   |
| .DS_Store | MacOS custom folder attributes |   |   |   |
| Thumbs.db | Windows thumbnail data         |   |   |   |

### yensuremembers

```
usage: yensuremembers [-h] -i INTERNAL_DOMAINS [-y {1.7,1.8,1.9}]
                      [--offline-check | --online-check] [--verbose]
                      [--dry-run]
                      userfile groupfile

Ensures each research group in a list has a common set of members with a particular role. For example:
   one user has a manager role in all groups.

positional arguments:
  userfile              Name of the user file
  groupfile             Name of the group file ("-" for standard input)

optional arguments:
  -h, --help            show this help message and exit
  -i INTERNAL_DOMAINS, --internal-domains INTERNAL_DOMAINS
                        Comma-separated list of internal email domains to the Yoda server
  -y {1.7,1.8,1.9}, --yoda-version {1.7,1.8,1.9}
                        Yoda version on the server (default: 1.7)
  --offline-check, -c   Only checks user file format
  --online-check, -C    Check mode (online): Verifies that all users in the user file exist.
  --verbose, -v         Verbose mode: print additional debug information.
  --dry-run, -d         Dry run mode: show what action would be taken.

        The user file is a text file. Each line has a role and an existing user account name,
        separated by ':':

        Roles are:

        'manager:'    = user that will be given the role of manager
        'member:'     = user that will be given the role of member with read/write
        'viewer:'     = user that will be given the role of viewer with read

        Example lines:
        manager:m.manager@uu.nl
        viewer:v.viewer@uu.nl

        The group file should have one group name on each line.
```

### ygrepgroups

```
usage: ygrepgroups [-h] [-y {1.7,1.8,1.9}] [-a] searchstring

Searches for groups by a search string

positional arguments:
  searchstring          The string to search for

optional arguments:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9}, --yoda-version {1.7,1.8,1.9}
                        Yoda version on the server (default: 1.7)
  -a, --all             Show all groups (not just research and vault groups)
```

### ygroupinfo

Prints the category and subcategory of a Yoda research group.

```
usage: ygroupinfo [-h] [-y {1.7,1.8,1.9}] groupname

Shows information about a Yoda research group

positional arguments:
  groupname

optional arguments:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9}, --yoda-version {1.7,1.8,1.9}
                        Yoda version on the server (default: 1.7)
```

### yimportgroups

```
usage: yimportgroups [-h] [-y {1.7,1.8,1.9}] -i INTERNAL_DOMAINS
                     [--offline-check | --online-check] [--allow-update]
                     [--delete] [--verbose] [--no-validate-domains]
                     csvfile

Creates a list of groups based on a CSV file

positional arguments:
  csvfile               Name of the CSV file

optional arguments:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9}, --yoda-version {1.7,1.8,1.9}
                        Yoda version on the server (default: 1.7)
  -i INTERNAL_DOMAINS, --internal-domains INTERNAL_DOMAINS
                        Comma-separated list of internal email domains to the Yoda server
  --offline-check, -c   Check mode (offline): verify CSV format only. Does not connect to iRODS and does not create groups
  --online-check, -C    Check mode (online): verify CSV format and that groups do not exist. Does not create groups.
  --allow-update, -u    Allows existing groups to be updated
  --delete, -d          Delete group members not in CSV file
  --verbose, -v         Show information as extracted from CSV file
  --no-validate-domains, -n
                        Do not validate email address domains

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
usage: yreport_collectionsize [-y {1.7,1.8,1.9}] [--help] [-h] [-r] [-R]
                              [-g GROUP_BY]
                              (-c COLLECTION | -H | -C COMMUNITY)

Shows a report of the size of all data objects in a (set of) collections

optional arguments:
  -y {1.7,1.8,1.9}, --yoda-version {1.7,1.8,1.9}
                        Yoda version on the server (default: 1.7)
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
usage: yreport_dataobjectspercollection [-h] [-y {1.7,1.8,1.9}] [-r ROOT] [-e]

Shows a report of number of data objects and subcollections per collection

optional arguments:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9}, --yoda-version {1.7,1.8,1.9}
                        Yoda version on the server (default: 1.7)
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
usage: yreport_intake [-h] [-y {1.7,1.8,1.9}] [-p] -s STUDY [-c CACHE]

Generates a report of the contents of an intake collection.

optional arguments:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9}, --yoda-version {1.7,1.8,1.9}
                        Yoda version on the server (default: 1.7)
  -p, --progress        Show progress updates.
  -s STUDY, --study STUDY
                        Study to process
  -c CACHE, --cache CACHE
                        Local cache directory. Can be used to retrieve
                        previously collected information on datasets, in order
                        to speed up report generation. The script will also
                        store newly collected dataset information in the
                        cache.
```

### yreport\_linecount

Prints a report of the number of lines per data object.

```
usage: yreport_linecount [-h] [-y {1.7,1.8,1.9}]
                         (-c COLLECTION | -d DATA_OBJECT)

Shows a report of the line counts of data objects.

optional arguments:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9}, --yoda-version {1.7,1.8,1.9}
                        Yoda version on the server (default: 1.7)
  -c COLLECTION, --collection COLLECTION
                        show line counts of all data objects in this
                        collection (recursive)
  -d DATA_OBJECT, --data-object DATA_OBJECT
                        show line count of only this data object
```

### yrmgroups

```
usage: yrmgroups [-h] [-y {1.7,1.8,1.9}] [--remove-data] [--check] [--verbose]
                 [--dry-run] [--continue-failure]
                 groupfile

Removes a list of (research) groups

positional arguments:
  groupfile             Name of the group file

optional arguments:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9}, --yoda-version {1.7,1.8,1.9}
                        Yoda version on the server (default: 1.7)
  --remove-data, -r     Remove any data from the group, if needed.
  --check, -c           Check mode: verifies groups exist, and checks if they are empty
  --verbose, -v         Verbose mode: print additional debug information.
  --dry-run, -d         Dry run mode: show what action would be taken.
  --continue-failure, -C
                        Continue if operations to remove collections or data objects return an error code

The group file is a text file, with one group name (e.g.: research-foo) on each line
```

### yrmusers

```
usage: yrmusers [-h] [-y {1.7,1.8,1.9}] [--check] [--verbose] [--dry-run]
                userfile

Removes a list of user accounts. This script needs to run locally on the environment.

positional arguments:
  userfile              Name of the user file

optional arguments:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9}, --yoda-version {1.7,1.8,1.9}
                        Yoda version on the server (default: 1.7)
  --check, -c           Check mode: verifies user exist and trash/home directories are empty
  --verbose, -v         Verbose mode: print additional debug information.
  --dry-run, -d         Dry run mode: show what action would be taken.

The user file is a text file, with one user name on each line.
```

### ywhichgroups

Prints a list of all groups a user is a member of.

```
usage: ywhichgroups [-h] [-y {1.7,1.8,1.9}] username

Returns a list of groups of which a user is a member

positional arguments:
  username              The username

optional arguments:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9}, --yoda-version {1.7,1.8,1.9}
                        Yoda version on the server (default: 1.7)
```
