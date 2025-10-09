# Change log

## 2025-10-09 v2.2.0

- Improve autodetection of CA certificate setting by checking whether iRODS
  certificate is self-signed, and only using the iRODS certificate as a CA
  certificate if that is the case.
- Upgrade Python-irodsclient to v3.2.0.
- Remove deprecated UserGroup / user_groups references, which have been removed
  in Python-irodsclient v3.2.0
- Provide fallback to Python-irodsclient v3.1.1 on Python versions
  older than 3.9 as a temporary workaround so that it still runs there.
- Drop official support for Python 3.8. It is end-of-life.

## 2025-08-25 v2.1.0

- Minor help text fix in old vs. new data report
- Add groups export tool (export groups and group memberships into a CSV file)
- Replace calls to deprecated/removed rule uuGroupGetMember, for compatibility with
  Yoda 2.0.x
- Drop support for Yoda 1.7

## 2025-06-18 v2.0.0

- Upgrade python-irodsclient to v3.1.1
- Minimum Yoda version: changed to 1.9.x
- Minimum Python version: changed to to 3.8
- Add depth-first collection removal tool (ydf_irm)
- Print dry run output for ydf_irm and yrmgroups to standard output consistently, so
  that output can be processed more conveniently using tools such as grep and sed.
- Add --force option to ydf_irm and yrmgroups

## 2025-05-26 v1.12.0

- add "data duplication" report - prints report that shows which directory trees appear
  both in a research and vault collection.

## 2025-05-07 v1.11.0

- add "old vs new data" report - prints report on total replica size of data objects,
  grouped by old (not recently modified) vs new (recently modified) data objects

## 2025-03-10 v1.10.0

- Use increased session timeout for group lifecycle report to reduce risks of timeouts.
- Add "2.0" to Yoda version parameter, to prepare for release of first alpha version of
  Yoda 2.0.
- Docs: update example expiration date for importgroups - it needs to be in the future.
  Also update metadata schema in example to latest version.
- Docs: add summary list of tools
- Fix autodetection of CA certificates by choosing the iRODS server certificate over
  the distribution CA certificates, if available, so that running the client tools on a
  (development) server with a self-signed certificate works as expected with default
  settings.
- Extended data package report: add research or deposit group name, category name
  and subcategory
- Extended data package report: add archiving date and time
- Extended data package report: ensure archiving date/time and publication date/time
  use the same timezone (UTC)

## 2025-02-17 v1.9.0

- Data package status report: fix for matching vault collections other than data
  package collections in some cases.
- Data package status report: report data package collections with no valid status
  correctly.
- Add "all" option for --internal-domains in ensuremembers and importgroups tool
- Add extended data package report: report information for all data packages regarding
  path, size, publication state and date, README file, license, access type,
  and metadata schema.

## 2024-12-24 v1.8.0

- Upgrade Python-irodsclient to v3.0.0
- Add pending deposit report

## 2024-12-06 v1.7.0

- Add support for deposit groups to group lifecycle report.

## 2024-12-03 v1.6.0

- Add revision statistics to the group lifecycle report. Size of research group in this report
  no longer includes revisions.

## 2024-11-21 v1.5.0

- Add some default values for the CA file location that also work in non-Yoda-server environments.

## 2024-10-14 v1.4.0

- Add support for new Python version of user exists rule (YDA-5393)
- Update Python-irodsclient to v2.1.0

## 2024-08-09 v1.3.0

- Add --human-readable option to group lifecycle report, and change default behaviour to not
  report sizes in human readable units.

## 2024-05-24 v1.2.0

- Group lifecycle report: add options to show size and last modified date of research
  and vault groups
- Fix prompt for password if no .irodsA file is available

## 2024-05-01 v1.1.2

- Importgroups: fix issue where domain validation was not performed even if it had not been disabled
- Importgroups: fix issue where username validation results were not processed correctly.

## 2024-04-18 v1.1.1

- Fix regression that broke the ensuremembers tool
- Ensuremembers: add message in verbose mode that confirms validation checks passed
- Importgroups: update check existing groups in update mode for Yoda 1.10

## 2024-04-08 v1.1.0

- Prepare for release of Yoda v1.10
- Add data package status report

## 2024-02-28 v1.0.1

- yimportgroups: bugfix for situation where legacy format CSV files with role suffixes where not processed
  correctly in case of multiple users with the same role (YDA-5612)
- yimportgroups: retain support for legacy format CSV files with role suffixes in Yoda 1.9 and higher.

## 2024-02-19 v1.0.0

First 1.x release

## v0.0.1

Pre-release versions
