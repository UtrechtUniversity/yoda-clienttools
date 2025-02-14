# -*- coding: utf-8 -*-

"""This class contains utility functions that process names of Yoda entities (e.g. category names, user names, etc.)
"""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import dns.resolver as resolver
import re
from typing import List, Optional, Tuple

from datetime import datetime

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache  # type: ignore[no-redef]


def is_valid_username(username: str, no_validate_domains: bool) -> Tuple[bool, Optional[str]]:
    """Is this name a valid username
    Returns whether valid and error
    """
    if username == "":  # empty value, should be ignored and not added to the list
        return True, None
    elif not is_email(username):
        return False, 'Username "{}" is not a valid email address.'.format(username)
    elif not (no_validate_domains or is_valid_domain(username.split("@")[1])):
        return (
            False,
            'Username "{}" failed DNS domain validation - domain does not exist or has no MX records.'.format(
                username
            ),
        )
    else:
        return True, None


def is_email(username: str) -> bool:
    return re.search(r"@.*[^\.]+\.[^\.]+$", username) is not None


@lru_cache(maxsize=100)
def is_valid_domain(domain: str) -> bool:
    try:
        return bool(resolver.query(domain, "MX"))
    except (resolver.NXDOMAIN, resolver.NoAnswer):
        return False


def is_valid_category(name: str) -> bool:
    """Is this name a valid (sub)category name?"""
    return re.search(r"^[a-zA-Z0-9\-_]+$", name) is not None


def is_valid_groupname(name: str) -> bool:
    """Is this name a valid group name (prefix such as "research-" can be omitted)"""
    return re.search(r"^[a-zA-Z0-9\-]+$", name) is not None


def is_internal_user(username: str, internal_domains: List[str]) -> bool:
    for domain in internal_domains:
        domain_pattern = "@{}$".format(domain)
        if domain == "all" or re.search(domain_pattern, username) is not None:
            return True

    return False


def is_valid_expiration_date(expiration_date: str) -> bool:
    """Validation of expiration date.

    :param expiration_date: String containing date that has to be validated

    :returns: Indication whether expiration date is an accepted value
    """
    # Copied from rule_group_expiration_date_validate
    if expiration_date in ["", "."]:
        return True

    try:
        if expiration_date != datetime.strptime(expiration_date, "%Y-%m-%d").strftime(
            "%Y-%m-%d"
        ):
            raise ValueError

        # Expiration date should be in the future
        if expiration_date <= datetime.now().strftime("%Y-%m-%d"):
            raise ValueError
        return True
    except ValueError:
        return False


def is_valid_schema_id(schema_id: str) -> bool:
    """Is this schema at least a correctly formatted schema-id?"""
    if schema_id == "":
        return True
    return re.search(r"^[a-zA-Z0-9\-]+\-[0-9]+$", schema_id) is not None
