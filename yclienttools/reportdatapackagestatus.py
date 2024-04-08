"""Produces a report of data packages and their vault status. The
   script can either report all data packages, or only the pending ones (i.e.
   ones with a status other than published, depublished or secured in the vault).
   The report can optionally be sent by email. An email is only sent if matching
   results have been found."""

import argparse
import json
import smtplib
import sys
import time

from irods.column import Like
from irods.models import Collection, CollectionMeta
from yclienttools import common_args, common_config
from yclienttools import session as s

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from math import floor


def entry():
    '''Entry point'''
    try:
        args = get_args()
        yoda_version = args.yoda_version if args.yoda_version is not None else common_config.get_default_yoda_version()
        session = s.setup_session(yoda_version)
        report_data_package_status(args, session)
        session.cleanup()

    except KeyboardInterrupt:
        print("Script interrupted by user.\n", file=sys.stderr)


def get_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--email",
        help="Comma-separated list of email addresses to send report to (default: print to stdout).")
    parser.add_argument(
        "--email-subject",
        default="Data package report",
        help="Subject for email reports, can include e.g. the name of the environment.")
    parser.add_argument(
        "--email-sender",
        default="noreply@uu.nl",
        help="Sender of emails (default: noreply@uu.nl)")
    parser.add_argument(
        "--pending",
        action="store_true",
        default=False,
        help="Only print pending data packages (i.e. not (de)published or secured)")
    parser.add_argument(
        "--stale",
        action="store_true",
        default=False,
        help="Only print data packages which have last been modified over approximately four hours ago (or with unavailable modification time)")
    common_args.add_default_args(parser)
    return parser.parse_args()


def send_email(recipients, sender, subject, contents):
    for recipient in recipients:
        message = MIMEMultipart()
        message['From'] = sender
        message['To'] = recipient
        message['Subject'] = subject
        message.attach(MIMEText(contents, 'plain'))
        connection = smtplib.SMTP("127.0.0.1", 25)
        connection.ehlo()
        connection.sendmail(sender, recipient, message.as_string())


def time_ago(old_timestamp, new_timestamp):
    """Returns how much time in (days, hours) is between two unix timestamps,
       rounded down to the nearest hour"""
    delta = new_timestamp - old_timestamp
    days = floor(delta / 86400)
    hours = round((delta % 86400) / 3600)
    return (days, hours)


def time_ago_to_readable(days, hours):
    """Returns human-readable description of output time_ago"""
    if days == 0 and hours == 0:
        return "Less than 1 hour ago"
    elif days == 0:
        return "Approximately " + str(hours) + " hour(s) ago."
    elif days < 3:
        return "Approximately " + \
            str(days) + " day(s) and " + str(hours) + " hours ago."
    else:
        return "Approximately " + str(days) + " days ago."


def report_data_package_status(args, session):
    report = ""
    for data_package in get_data_packages(session):

        status = get_vault_status(session, data_package)
        if args.pending and status in [
                "COMPLETE", "PUBLISHED", "UNPUBLISHED", "DEPUBLISHED"]:
            continue

        latest_timestamp = get_latest_action_timestamp(session, data_package)
        if latest_timestamp is None:
            (days_ago, hours_ago) = (0, 0)
            human_readable_ago = "N/A"
        else:
            (days_ago, hours_ago) = time_ago(get_latest_action_timestamp(session, data_package),
                                             get_current_timestamp())
            human_readable_ago = time_ago_to_readable(days_ago, hours_ago)

        if args.stale and days_ago == 0 and hours_ago <= 4:
            continue

        line = data_package + " : " + human_readable_ago + " : " + status
        if args.email is None:
            print(line)
        else:
            report += line + "\n"

    if args.email is not None and report != "":
        send_email(
            args.email.split(","),
            args.email_sender,
            args.email_subject,
            report)


def get_data_packages(session):
    """Returns a list of collections of all data packages."""
    query_results = session.query(Collection.name).filter(
        Like(Collection.parent_name, '/%/home/vault-%')).filter(
        CollectionMeta.name == 'org_vault_status').get_results()

    return [result[Collection.name]
            for result in query_results if not result[Collection.name].endswith("/original")]


def get_current_timestamp():
    return time.time()


def get_latest_action_timestamp(session, collection):
    """Returns timestamp of latest action for data package (or None if no actions found)."""
    latest_timestamp = None
    collection_data = list(session.query(CollectionMeta.value).filter(
        Collection.name == collection).filter(
        CollectionMeta.name == 'org_action_log').get_results())

    for result in collection_data:
        try:
            log_entry = json.loads(result[CollectionMeta.value])
            timestamp = int(log_entry[0])
            if latest_timestamp is None or latest_timestamp < timestamp:
                latest_timestamp = timestamp
        except KeyError:
            print(
                f"Warning: cannot find timestamp entry for action in {collection}.")
        except json.decoder.JSONDecodeError:
            print(
                f"Warning cannot parse action data for action in {collection}.")

    return latest_timestamp


def get_vault_status(session, collection):
    """Returns org_vault_status of data package (or None if not found)"""
    query_results = list(session.query(CollectionMeta.value).filter(
        Collection.name == collection).filter(
        CollectionMeta.name == 'org_vault_status').get_results())

    if len(query_results) == 1:
        return query_results[0][CollectionMeta.value]
    else:
        return None
