# -*- coding: utf-8 -*-

"""Unit tests for import groups script
"""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append("../yclienttools")

from yoda_names import is_internal_user, is_valid_category, is_valid_subcategory, is_valid_groupname


class YodaNamesTest(TestCase):
    def test_is_internal_user(self):
        self.assertEqual(is_internal_user("user@test.org", []), False)
        self.assertEqual(is_internal_user("user@test.org", ["test.org"]), True)
        self.assertEqual(is_internal_user("user@test.org", ["test.com"]), False)
        self.assertEqual(is_internal_user("user@test.org", ["all"]), True)

    def is_valid_category(self):
        self.assertEqual(is_valid_category("lowercaseletters"), True)
        self.assertEqual(is_valid_category("lowercase-withdash"), True)
        self.assertEqual(is_valid_category("lowercase.withdot"), False)
        self.assertEqual(is_valid_category("lowercase,withcomma"), False)
        self.assertEqual(is_valid_category("lowercase_withunderscore"), False)
        self.assertEqual(is_valid_category("lowercase(withparentheses)"), False)
        self.assertEqual(is_valid_category("lowercase with spaces"), False)
        self.assertEqual(is_valid_category("lowercase-withnumbersanddash-123"), True)
        self.assertEqual(is_valid_category("lowercase-endswithdash-"), False)
        self.assertEqual(is_valid_category("-lowercase-beginswithdash"), False)
        self.assertEqual(is_valid_category("MiXeDcASe"), False)
        self.assertEqual(is_valid_category("toolong" + 2700 * "a"), False)

    def is_valid_subcategory(self):
        self.assertEqual(is_valid_subcategory("lowercaseletters"), True)
        self.assertEqual(is_valid_subcategory("lowercase-withdash"), True)
        self.assertEqual(is_valid_subcategory("lowercase.withdot"), True)
        self.assertEqual(is_valid_subcategory("lowercase,withcomma"), True)
        self.assertEqual(is_valid_subcategory("lowercase_withunderscore"), True)
        self.assertEqual(is_valid_subcategory("lowercase(withparentheses)"), True)
        self.assertEqual(is_valid_subcategory("lowercase with spaces"), True)
        self.assertEqual(is_valid_subcategory("lowercase-withnumbersanddash-123"), True)
        self.assertEqual(is_valid_subcategory("lowercase-endswithdash-"), True)
        self.assertEqual(is_valid_subcategory("-lowercase-beginswithdash"), True)
        self.assertEqual(is_valid_subcategory("MiXeDcASe"), True)
        self.assertEqual(is_valid_subcategory("toolong" + 2700 * "a"), False)

    def is_valid_groupname(self):
        self.assertEqual(is_valid_groupname("research-lowercaseletters"), True)
        self.assertEqual(is_valid_groupname("research-lowercase-withdash"), True)
        self.assertEqual(is_valid_groupname("research-lowercase.withdot"), False)
        self.assertEqual(is_valid_groupname("research-lowercase,withcomma"), False)
        self.assertEqual(is_valid_groupname("research-lowercase_withunderscore"), False)
        self.assertEqual(is_valid_groupname("research-lowercase(withparentheses)"), False)
        self.assertEqual(is_valid_groupname("research-lowercase with spaces"), False)
        self.assertEqual(is_valid_groupname("research-lowercase-withnumbersanddash-123"), True)
        self.assertEqual(is_valid_groupname("research-lowercase-endswithdash-"), False)
        self.assertEqual(is_valid_groupname("-lowercase-beginswithdash"), False)
        self.assertEqual(is_valid_groupname("research-MiXeDcASe"), False)
        self.assertEqual(is_valid_groupname("toolong" + 57 * "a"), False)
