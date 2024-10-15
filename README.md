# Yoda-clienttools

The Yoda client tools are a set of commandline utilities for Yoda. They are mainly
intended for data managers and key users.

## Installation

These tools require Python 3. They are compatible with Yoda 1.7.x through 1.10.x.

### Linux

It is recommended to install the tools in a virtual environment, like this:

```
python3 -m venv venv
source venv/bin/activate
pip3 install --upgrade git+https://github.com/UtrechtUniversity/yoda-clienttools.git
```

See also the `Configuration` section below.


### Windows

For Windows users, please activate Windows Subsystem for Linux and install Ubuntu as described on the Microsoft page https://learn.microsoft.com/en-us/windows/wsl/install. You will also need to install iCommands within your Ubuntu distro as described at https://www.uu.nl/en/research/yoda/guide-to-yoda/i-am-using-yoda/using-icommands-for-large-datasets. You will additionally need to create a .irods folder in your Ubuntu home directory (`mkdir .irods`) and create an irods_environment.json file (`sudo nano irods_environment.json`). The contents of that json file can be found after logging in to the Yoda webportal and clicking on the Yoda version at the bottom of each page in the webportal (e.g., clicking on Yoda `v1.8.6` or `Yoda v1.9`).

Once you have completed the previous steps and have Ubuntu up and running, run the following commands:

```
sudo apt update
sudo apt install python3 python3-pip python3.8-venv
```

Then install the tools in a virtual environment:

```
/usr/bin/python3.8 -m venv yodatoolsvenv
source yodatoolsvenv/bin/activate
pip install wheel
pip install --upgrade git+https://github.com/UtrechtUniversity/yoda-clienttools.git

```

Create a configuration file named `.yodaclienttools.yml` in your home directory that overrides the CA path to the Ubuntu location, like so:

```yaml
ca_file: /etc/ssl/certs/ca-certificates.crt
```

You are now good to go. When you run the client tools, make sure you first run `iinit` to sign in to Yoda first

## Configuration

The Yoda client tools look for an optional configuration file in YAML format named `.yodaclienttools.yml` in the user's home directory

Example:

```
ca_file: /etc/ssl/certs/ca-certificates.crt
default_yoda_version: 1.8
```

The following parameters are available:
- `ca_file` : the name of the local Certificate Authority (CA) file, which is used to verify the Yoda server's identity. It uses the
   CentOS / RHEL CA File location by default.
- `default_yoda_version`: the Yoda client tools need to know the Yoda version running on the server. This version can be provided when running a tool
   using the `--yoda-version` parameter. When this parameter is not provided, the tools use the default version specified in the configuration file, or
   `1.8` if no default version is configured.

## Running tests

There are a few unit tests in `unit-tests` using the [unittest framework](https://docs.python.org/3/library/unittest.html), they are run directly against the files in the `yclienttools` directory. For example:

```bash
$ cd unit-tests
$ python -m unittest unit_tests
.
----------------------------------------------------------------------
Ran 3 tests in 0.002s

OK
```

## Overview of tools

### ycleanup\_files

```
usage: ycleanup_files [-h] [-y {1.7,1.8,1.9,1.10}] -r ROOT

Recursively finds data objects in a collection that will typically have to be
cleaned up when a dataset is archived, and deletes them.

options:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
  -r ROOT, --root ROOT  Delete unwanted files in this collection, as well as
                        its subcollections

```
Overview of files to be removed:

| file      | meaning                        |   |   |   |
|-----------|--------------------------------|---|---|---|
| .\_*      | MacOS resource fork            |   |   |   |
| .DS_Store | MacOS custom folder attributes |   |   |   |
| Thumbs.db | Windows thumbnail data         |   |   |   |

### yensuremembers

```
usage: yensuremembers [-h] [-y {1.7,1.8,1.9,1.10}] -i INTERNAL_DOMAINS
                      [--offline-check | --online-check] [--verbose]
                      [--dry-run]
                      userfile groupfile

Ensures each research group in a list has a common set of members with a particular role. For example:
   one user has a manager role in all groups.

positional arguments:
  userfile              Name of the user file
  groupfile             Name of the group file ("-" for standard input)

options:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
  -i INTERNAL_DOMAINS, --internal-domains INTERNAL_DOMAINS
                        Comma-separated list of internal email domains to the Yoda server
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
usage: ygrepgroups [-h] [-y {1.7,1.8,1.9,1.10}] [-a] searchstring

Searches for groups by a search string

positional arguments:
  searchstring          The string to search for

options:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
  -a, --all             Show all groups (not just research and vault groups)
```

### ygroupinfo

Prints the category and subcategory of a Yoda research group.

```
usage: ygroupinfo [-h] [-y {1.7,1.8,1.9,1.10}] groupname

Shows information about a Yoda research group

positional arguments:
  groupname

options:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
```

### yimportgroups

```
usage: yimportgroups [-h] [-y {1.7,1.8,1.9,1.10}] -i INTERNAL_DOMAINS
                     [--offline-check | --online-check] [--allow-update]
                     [--delete] [--verbose] [--no-validate-domains]
                     [--creator-user CREATOR_USER]
                     [--creator-zone CREATOR_ZONE]
                     csvfile

Creates a list of groups based on a CSV file

positional arguments:
  csvfile               Name of the CSV file

options:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
  -i INTERNAL_DOMAINS, --internal-domains INTERNAL_DOMAINS
                        Comma-separated list of internal email domains to the Yoda server
  --offline-check, -c   Check mode (offline): verify CSV format only. Does not connect to iRODS and does not create groups
  --online-check, -C    Check mode (online): verify CSV format and that groups do not exist. Does not create groups.
  --allow-update, -u    Allows existing groups to be updated
  --delete, -d          Delete group members not in CSV file
  --verbose, -v         Show information as extracted from CSV file
  --no-validate-domains, -n
                        Do not validate email address domains
  --creator-user CREATOR_USER
                        User who creates user (only available in Yoda 1.9 and higher)
  --creator-zone CREATOR_ZONE
                        Zone of the user who creates user (only available in Yoda 1.9 and higher)

        The CSV file is expected to include the following labels in its header (the first row):
        'category'        = category for the group
        'subcategory'     = subcategory for the group
        'groupname'       = name of the group (without the "research-" prefix)

        For Yoda versions 1.9 and higher, these labels can optionally be included:
        'expiration_date' = expiration date for the group. Can only be set when the group is first created.
        'schema_id'       = schema id for the group. Can only be set when the group is first created.

        The remainder of the columns should be labels that indicate the role of each group member:
        'manager'         = user that will be given the role of manager
        'member'          = user that will be given the role of member with read/write
        'viewer'          = user that will be given the role of viewer with read

        Notes:
        - Columns may appear in any order
        - Empty data cells are ignored: groups can differ in number of members
        - manager, member, and viewer columns can appear multiple times

        Example:
        category,subcategory,groupname,manager,member,member
        departmentx,teama,groupteama,m.manager@example.com,m.member@example.com,n.member@example.com
        departmentx,teamb,groupteamb,m.manager@example.com,p.member@example.com,

        Example Yoda 1.9 and higher:
        category,subcategory,groupname,manager,member,expiration_date,schema_id
        departmentx,teama,groupteama,m.manager@example.com,m.member@example.com,2025-01-01,default-2
        departmentx,teamb,groupteamb,m.manager@example.com,p.member@example.com,,

```

### yreport\_collectionsize

Shows a report of the size of all data objects in a (set of) collections.

```
usage: yreport_collectionsize [-y {1.7,1.8,1.9,1.10}] [--help] [-q] [-h] [-r]
                              [-R] [-g GROUP_BY]
                              (-c COLLECTION | -H | -C COMMUNITY)

Shows a report of the size of all data objects in a (set of) collections

options:
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
  --help                show help information
  -q, --quasi-xml       Enable Quasi-XML parser in order to be able to parse
                        characters not supported by regular XML parser
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
                        Argument should be 'none' (the default), 'resource'
                        or 'location'. Grouping by resource or location
                        implies --count-all-replicas. If a collection has no
                        dataobjects and --group-by resource / location is
                        enabled, its size will be printed with group 'all'.
  -c COLLECTION, --collection COLLECTION
                        Show total size of data objects in this collection
                        and its subcollections
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
usage: yreport_dataobjectspercollection [-h] [-y {1.7,1.8,1.9,1.10}]
                                        [-r ROOT] [-e]

Shows a report of number of data objects and subcollections per collection

options:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
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

### yreport_datapackagestatus

```
usage: yreport_datapackagestatus [-h] [--email EMAIL]
                                 [--email-subject EMAIL_SUBJECT]
                                 [--email-sender EMAIL_SENDER] [--pending]
                                 [--stale] [-y {1.7,1.8,1.9,1.10}]

Produces a report of data packages and their vault status. The script can
either report all data packages, or only the pending ones (i.e. ones with a
status other than published, depublished or secured in the vault). The report
can optionally be sent by email. An email is only sent if matching results
have been found.

optional arguments:
  -h, --help            show this help message and exit
  --email EMAIL         Comma-separated list of email addresses to send report
                        to (default: print to stdout).
  --email-subject EMAIL_SUBJECT
                        Subject for email reports, can include e.g. the name
                        of the environment.
  --email-sender EMAIL_SENDER
                        Sender of emails (default: noreply@uu.nl)
  --pending             Only print pending data packages (i.e. not
                        (de)published or secured)
  --stale               Only print data packages which have last been modified
                        over approximately four hours ago (or with unavailable
                        modification time)
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
```

### yreport\_grouplifecycle

```
usage: yreport_grouplifecycle [-h] [-q] [-s] [-H] [-m] [-y {1.7,1.8,1.9,1.10}]

Generates a list of research groups, along with their creation date,
expiration date (if available), lists of group managers, regular members, and
readonly members. The report also shows whether each research compartment
contains data, as well as whether its vault compartment contains data. The
report can optionally include size and last modified date of both the research
and vault collection.

optional arguments:
  -h, --help            show this help message and exit
  -q, --quasi-xml       Enable Quasi-XML parser in order to be able to parse
                        characters not supported by regular XML parser
  -s, --size            Include size of research collection and vault
                        collection in output
  -H, --human-readable  Report sizes in human-readable figures (only relevant
                        in combination with --size parameter)
  -m, --modified        Include last modified date research collection and
                        vault collection in output
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
```

### yreport\_intake

Prints an intake collection report. This report is only relevant for environments
that use the intake module.

On systems with a significant number of datasets, it is recommended to use the
--cache parameter to keep a local cache of dataset statistics in order to speed
up report generation.

```
usage: yreport_intake [-h] [-y {1.7,1.8,1.9,1.10}] [-p] -s STUDY [-c CACHE]

Generates a report of the contents of an intake collection.

options:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
  -p, --progress        Show progress updates.
  -s STUDY, --study STUDY
                        Study to process
  -c CACHE, --cache CACHE
                        Local cache directory. Can be used to retrieve
                        previously collected information on datasets, in
                        order to speed up report generation. The script will
                        also store newly collected dataset information in the
                        cache.
```

### yreport\_linecount

Prints a report of the number of lines per data object.

```
usage: yreport_linecount [-h] [-y {1.7,1.8,1.9,1.10}]
                         (-c COLLECTION | -d DATA_OBJECT)

Shows a report of the line counts of data objects.

options:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
  -c COLLECTION, --collection COLLECTION
                        show line counts of all data objects in this
                        collection (recursive)
  -d DATA_OBJECT, --data-object DATA_OBJECT
                        show line count of only this data object
```

### yrmgroups

```
usage: yrmgroups [-h] [-y {1.7,1.8,1.9,1.10}] [--remove-data] [--check]
                 [--verbose] [--dry-run] [--continue-failure]
                 groupfile

Removes a list of (research) groups

positional arguments:
  groupfile             Name of the group file

options:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
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
usage: yrmusers [-h] [-y {1.7,1.8,1.9,1.10}] [--check] [--verbose]
                [--dry-run]
                userfile

Removes a list of user accounts. This script needs to run locally on the environment.

positional arguments:
  userfile              Name of the user file

options:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
  --check, -c           Check mode: verifies user exist and trash/home directories are empty
  --verbose, -v         Verbose mode: print additional debug information.
  --dry-run, -d         Dry run mode: show what action would be taken.

The user file is a text file, with one user name on each line.
```

### ywhichgroups

Prints a list of all groups a user is a member of.

```
usage: ywhichgroups [-h] [-y {1.7,1.8,1.9,1.10}] username

Returns a list of groups of which a user is a member

positional arguments:
  username              The username

options:
  -h, --help            show this help message and exit
  -y {1.7,1.8,1.9,1.10}, --yoda-version {1.7,1.8,1.9,1.10}
                        Override Yoda version on the server
```
