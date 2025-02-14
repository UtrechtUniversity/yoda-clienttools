# -*- coding: utf-8 -*-

"""Unit tests for import groups script
"""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append("../yclienttools")

from yoda_names import is_internal_user


class YodaNamesTest(TestCase):
    def test_is_internal_user(self):
        self.assertEqual(is_internal_user("user@test.org", []), False)
        self.assertEqual(is_internal_user("user@test.org", ["test.org"]), True)
        self.assertEqual(is_internal_user("user@test.org", ["test.com"]), False)
        self.assertEqual(is_internal_user("user@test.org", ["all"]), True)
