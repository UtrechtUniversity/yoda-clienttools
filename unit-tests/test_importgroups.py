# -*- coding: utf-8 -*-

"""Unit tests for import groups script
"""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import argparse
from io import StringIO
import sys
from unittest import TestCase
from unittest.mock import patch

sys.path.append("../yclienttools")

from importgroups import _get_duplicate_columns, _get_duplicate_groups, _process_csv_line, parse_csv_file  # type: ignore[import-not-found]


class ImportGroupsTest(TestCase):
    def test_duplicate_columns(self):
        columns = ["category", "subcategory", "groupname", "category"]
        result = _get_duplicate_columns(columns, "1.8")
        self.assertSetEqual(result, set({"category"}))

    def test_fully_filled_csv_line_1_9(self):
        args = {"offline_check": True, "no_validate_domains": True}
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager": ["m.manager@yoda.dev"],
            "member": ["p.member@yoda.dev"],
            "viewer": ["m.viewer@yoda.dev"],
            "expiration_date": ["2030-01-01"],
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
            "2030-01-01",
        )
        result, error_msg = _process_csv_line(d, argparse.Namespace(**args), "1.9")
        self.assertTupleEqual(expected, result)
        self.assertIsNone(error_msg)

    def test_fully_filled_csv_line_1_9_multi_role(self):
        args = {"offline_check": True, "no_validate_domains": True}
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager": ["m.manager@yoda.dev", "n.manager@yoda.dev"],
            "member": ["p.member@yoda.dev", "q.member@yoda.dev"],
            "viewer": ["m.viewer@yoda.dev", "n.viewer@yoda.dev"],
            "expiration_date": ["2030-01-01"],
            "schema_id": ["default-3"],
        }
        expected = (
            "test-automation",
            "initial",
            "research-groupteama",
            ["m.manager@yoda.dev", "n.manager@yoda.dev"],
            ["p.member@yoda.dev", "q.member@yoda.dev"],
            ["m.viewer@yoda.dev", "n.viewer@yoda.dev"],
            "default-3",
            "2030-01-01",
        )
        result, error_msg = _process_csv_line(d, argparse.Namespace(**args), "1.9")
        self.assertTupleEqual(expected, result)
        self.assertIsNone(error_msg)

    def test_fully_filled_csv_line_1_9_with_suffixes(self):
        # Confirm support the old csv header format still (with ":nicknameofuser")
        args = {"offline_check": True, "no_validate_domains": True}
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager:alice": ["m.manager@yoda.dev"],
            "member:bob": ["p.member@yoda.dev"],
            "viewer:eve": ["m.viewer@yoda.dev"],
            "expiration_date": ["2030-01-01"],
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
            "2030-01-01",
        )
        result, error_msg = _process_csv_line(d, argparse.Namespace(**args), "1.9")
        self.assertTupleEqual(expected, result)
        self.assertIsNone(error_msg)

    def test_fully_filled_csv_line_1_9_with_suffixes_multi_role(self):
        # Confirm support the old csv header format still (with ":nicknameofuser")
        args = {"offline_check": True, "no_validate_domains": True}
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager:alice": ["m.manager@yoda.dev"],
            "manager:andy": ["n.manager@yoda.dev"],
            "member:bob": ["p.member@yoda.dev"],
            "member:bella": ["q.member@yoda.dev"],
            "viewer:eve": ["m.viewer@yoda.dev"],
            "viewer:emma": ["n.viewer@yoda.dev"],
            "expiration_date": ["2030-01-01"],
            "schema_id": ["default-3"],
        }
        expected = (
            "test-automation",
            "initial",
            "research-groupteama",
            ["m.manager@yoda.dev", "n.manager@yoda.dev"],
            ["p.member@yoda.dev", "q.member@yoda.dev"],
            ["m.viewer@yoda.dev", "n.viewer@yoda.dev"],
            "default-3",
            "2030-01-01",
        )
        result, error_msg = _process_csv_line(d, argparse.Namespace(**args), "1.9")
        self.assertTupleEqual(expected, result)
        self.assertIsNone(error_msg)

    def test_missing_fields_1_9(self):
        args = {"offline_check": True, "no_validate_domains": True}
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
        result, error_msg = _process_csv_line(d, argparse.Namespace(**args), "1.9")
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
        result, error_msg = _process_csv_line(d, argparse.Namespace(**args), "1.9")
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
        result, error_msg = _process_csv_line(d, argparse.Namespace(**args), "1.9")
        self.assertIsNone(result)
        self.assertIn("missing", error_msg)

    def test_error_fields_1_8(self):
        args = {"offline_check": True, "no_validate_domains": True}
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
        result, error_msg = _process_csv_line(d, argparse.Namespace(**args), "1.8")
        self.assertIsNone(result)
        self.assertIn("1.9", error_msg)

    def test_parse_csv(self):
        args = {"offline_check": True, "no_validate_domains": True}
        parse_csv_file("files/csv-import-test.csv", argparse.Namespace(**args), "1.9")

        # With carriage returns
        parse_csv_file("files/windows-csv.csv", argparse.Namespace(**args), "1.9")

    @patch('sys.stderr', new_callable=StringIO)
    def test_parse_csv_with_header_suffixes(self, mock_stderr):
        args = {"offline_check": True, "no_validate_domains": True}
        parse_csv_file("files/header-with-suffixes.csv", argparse.Namespace(**args), "1.8")

    @patch('sys.stderr', new_callable=StringIO)
    def test_parse_invalid_csv_file(self, mock_stderr):
        # csv that has an unlabeled header
        args = {"offline_check": True, "no_validate_domains": True}
        with self.assertRaises(SystemExit):
            parse_csv_file("files/unlabeled-column.csv", argparse.Namespace(**args), "1.9")

        # csv that has too many items in the rows compared to the headers
        with self.assertRaises(SystemExit):
            parse_csv_file("files/more-entries-than-headers.csv", argparse.Namespace(**args), "1.9")

    def test_parse_duplicate_groups(self):
        args = {"offline_check": True, "no_validate_domains": True}

        data_no_duplicates = parse_csv_file("files/no-duplicates.csv", argparse.Namespace(**args), "1.9")
        self.assertEqual(_get_duplicate_groups(data_no_duplicates), [])

        data_with_duplicates = parse_csv_file("files/with-duplicates.csv", argparse.Namespace(**args), "1.9")
        self.assertEqual(_get_duplicate_groups(data_with_duplicates), ["research-data-duplicate"])
