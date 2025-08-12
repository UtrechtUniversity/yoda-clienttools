# -*- coding: utf-8 -*-

"""Unit tests for export groups script
"""

__copyright__ = 'Copyright (c) 2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append("../yclienttools")

from exportgroups import _create_output_row  # type: ignore[import-not-found]


class ExportGroupsTest(TestCase):
    def test_output_row(self):
        rowdata = {
            "category": "test",
            "subcategory": "testsubcat",
            "groupname": "test-group",
            "schema_id": "default-3",
            "member": ["researcher"],
            "manager": ["groupmanager"],
            "viewer": []
        }
        max_counts = {
            "member": 3,
            "manager": 3,
            "viewer": 0
        }
        result = _create_output_row(rowdata, max_counts)
        expected = [
            "test",
            "testsubcat",
            "test-group",
            "default-3",
            None,
            "groupmanager",
            None,
            None,
            "researcher",
            None,
            None
        ]
        self.assertListEqual(result, expected)
