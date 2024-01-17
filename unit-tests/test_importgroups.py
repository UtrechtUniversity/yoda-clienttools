# -*- coding: utf-8 -*-

"""Unit tests for import groups script
"""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase
from unittest.mock import patch
from io import StringIO

sys.path.append("../yclienttools")

from importgroups import _get_duplicate_columns, _process_csv_line, parse_csv_file


class ImportGroupsTest(TestCase):
    def test_duplicate_columns(self):
        columns = ["category", "subcategory", "groupname", "category"]
        result = _get_duplicate_columns(columns, "1.8")
        self.assertSetEqual(result, set({"category"}))

    def test_fully_filled_csv_line_1_9(self):
        args = {"offline_check": True}
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager": ["m.manager@yoda.dev"],
            "member": ["p.member@yoda.dev"],
            "viewer": ["m.viewer@yoda.dev"],
            "expiration_date": ["2025-01-01"],
            "schema_id": ["default-3"],
        }
        expected = (
            "test-automation",
            "initial",
            "research-groupteama",
            ["m.manager@yoda.dev"],
            ["p.member@yoda.dev"],
            ["m.viewer@yoda.dev"],
            "default-3",
            "2025-01-01",
        )
        result, error_msg = _process_csv_line(d, args, "1.9")
        self.assertTupleEqual(expected, result)
        self.assertIsNone(error_msg)

    def test_missing_fields_1_9(self):
        args = {"offline_check": True}
        # No schema id or expiration date
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager": ["m.manager@yoda.dev"],
            "member": ["p.member@yoda.dev"],
            "viewer": ["m.viewer@yoda.dev"],
        }
        expected = (
            "test-automation",
            "initial",
            "research-groupteama",
            ["m.manager@yoda.dev"],
            ["p.member@yoda.dev"],
            ["m.viewer@yoda.dev"],
            "",
            "",
        )
        result, error_msg = _process_csv_line(d, args, "1.9")
        self.assertTupleEqual(expected, result)
        self.assertIsNone(error_msg)

        # schema id, expiration date empty strings (should not give an error)
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager": ["m.manager@yoda.dev"],
            "member": ["p.member@yoda.dev"],
            "viewer": ["m.viewer@yoda.dev"],
            "schema_id": [""],
            "expiration_date": [""],
        }
        expected = (
            "test-automation",
            "initial",
            "research-groupteama",
            ["m.manager@yoda.dev"],
            ["p.member@yoda.dev"],
            ["m.viewer@yoda.dev"],
            "",
            "",
        )
        result, error_msg = _process_csv_line(d, args, "1.9")
        self.assertTupleEqual(expected, result)
        self.assertIsNone(error_msg)

        # Missing subcategory (should give error)
        d = {
            "category": ["test-automation"],
            "groupname": ["groupteama2"],
            "manager": ["m.manager@yoda.dev"],
            "member": ["m.member@yoda.dev", "m.member2@yoda.dev"],
            "expiration_date": ["2030-01-01"],
            "schema_id": ["default-3"],
        }
        result, error_msg = _process_csv_line(d, args, "1.9")
        self.assertIsNone(result)
        self.assertIn("missing", error_msg)

    def test_error_fields_1_8(self):
        args = {"offline_check": True}
        # Includes (valid) schema id and expiration,
        # which are not in version 1.8 (should give error)
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager": ["m.manager@yoda.dev"],
            "member": ["p.member@yoda.dev"],
            "viewer": ["m.viewer@yoda.dev"],
            "schema_id": ["default-3"],
            "expiration_date": ["2030-01-01"],
        }
        result, error_msg = _process_csv_line(d, args, "1.8")
        self.assertIsNone(result)
        self.assertIn("1.9", error_msg)

    @patch('sys.stderr', new_callable=StringIO)
    def test_parse_invalid_csv_file(self, mock_stderr):
        # csv that has an unlabeled header
        args = {"offline_check": True}
        with self.assertRaises(SystemExit):
            parse_csv_file("files/unlabeled-column.csv", args, "1.9")

        # csv that has too many items in the rows compared to the headers
        with self.assertRaises(SystemExit):
            parse_csv_file("files/more-entries-than-headers.csv", args, "1.9")
