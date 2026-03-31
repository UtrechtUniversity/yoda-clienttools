# -*- coding: utf-8 -*-
"""
Unit tests for recategorize groups script (recatgroups.py)
"""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
import tempfile
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

sys.path.append("../yclienttools")

from recatgroups import (
    _normalize_category,
    _split_datamanagers,
    parse_csv_file_recat,
)


class RecatGroupsTest(TestCase):
    def _write_tmp_csv(self, content: str) -> str:
        f = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", newline="")
        f.write(content)
        f.flush()
        f.close()
        return f.name

    def test_normalize_category(self):
        self.assertEqual(_normalize_category(" Dept.X "), "deptx")
        self.assertEqual(_normalize_category("test-automation"), "test-automation")
        self.assertEqual(_normalize_category(""), "")

    def test_split_datamanagers(self):
        self.assertEqual(_split_datamanagers(""), [])
        self.assertEqual(_split_datamanagers("alice@example.org"), ["alice@example.org"])
        self.assertEqual(
            _split_datamanagers(" alice@example.org ; bob@example.org;; "),
            ["alice@example.org", "bob@example.org"],
        )

    def test_parse_valid_csv_comma(self):
        path = self._write_tmp_csv(
            "groupname,category,subcategory\n"
            "research-groupa,test-automation,initial\n"
            "research-groupb,test-automation,\n"
        )
        data = parse_csv_file_recat(path)
        self.assertEqual(len(data), 2)

        self.assertEqual(data[0][0], "research-groupa")
        self.assertEqual(data[0][1], "test-automation")
        self.assertEqual(data[0][2], "initial")
        self.assertEqual(data[0][3], 2)  # line number in the CSV file

        self.assertEqual(data[1][0], "research-groupb")
        self.assertEqual(data[1][2], "")  # unchanged/empty subcategory
        self.assertEqual(data[1][3], 3)

    @patch("sys.stderr", new_callable=StringIO)
    def test_parse_missing_header(self, mock_stderr):
        path = self._write_tmp_csv(
            "groupname,category,\n"
            "research-groupa,test-automation,\n"
        )
        with self.assertRaises(SystemExit):
            parse_csv_file_recat(path)

    @patch("sys.stderr", new_callable=StringIO)
    def test_parse_unknown_header(self, mock_stderr):
        path = self._write_tmp_csv(
            "groupname,category,subcategory,unknown\n"
            "research-groupa,test-automation,initial,x\n"
        )
        with self.assertRaises(SystemExit):
            parse_csv_file_recat(path)

    @patch("sys.stderr", new_callable=StringIO)
    def test_parse_too_many_columns(self, mock_stderr):
        path = self._write_tmp_csv(
            "groupname,category,subcategory\n"
            "research-groupa,test-automation,initial,EXTRA\n"
        )
        with self.assertRaises(SystemExit):
            parse_csv_file_recat(path)

    @patch("sys.stderr", new_callable=StringIO)
    def test_parse_duplicate_groupname(self, mock_stderr):
        path = self._write_tmp_csv(
            "groupname,category,subcategory,datamanager\n"
            "research-groupa,test-automation,initial,\n"
            "research-groupa,test-automation,initial,\n"
        )
        with self.assertRaises(SystemExit):
            parse_csv_file_recat(path)

    @patch("sys.stderr", new_callable=StringIO)
    def test_parse_non_research_group_rejected(self, mock_stderr):
        path = self._write_tmp_csv(
            "groupname,category,subcategory,datamanager\n"
            "notresearch-groupa,test-automation,initial,\n"
        )
        with self.assertRaises(SystemExit):
            parse_csv_file_recat(path)
