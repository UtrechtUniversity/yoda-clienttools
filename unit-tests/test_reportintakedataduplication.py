# -*- coding: utf-8 -*-

"""Unit tests for intake data duplication report script
"""

__copyright__ = 'Copyright (c) 2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append("../yclienttools")

from reportintakedataduplication import get_duplicates  # type: ignore[import-not-found]


class IntakeDataDuplicationReportTest(TestCase):
    def test_get_duplicates_empty(self):
        self.assertEqual(get_duplicates([], []), [])

    def test_get_duplicates_no_duplicates(self):
        object1 = self._get_test_object(dataobj="1.dat", checksum="123")
        object2 = self._get_test_object(dataobj="2.dat", checksum="456", coll="/tempZone/home/intake-foo")
        self.assertEqual(get_duplicates([object1], [object2]), [])

    def test_get_duplicates_no_duplicates_only_name_different(self):
        object1 = self._get_test_object(dataobj="1.dat", checksum="123")
        object2 = self._get_test_object(dataobj="2.dat", checksum="123", coll="/tempZone/home/intake-foo")
        self.assertEqual(get_duplicates([object1], [object2]), [])

    def test_get_duplicates_no_duplicates_only_checksum_different(self):
        object1 = self._get_test_object(dataobj="1.dat", checksum="123")
        object2 = self._get_test_object(dataobj="1.dat", checksum="456", coll="/tempZone/home/intake-foo")
        self.assertEqual(get_duplicates([object1], [object2]), [])

    def test_get_duplicates_one_duplicate(self):
        object1 = self._get_test_object(dataobj="1.dat", checksum="123")
        object2 = self._get_test_object(dataobj="1.dat", checksum="123", coll="/tempZone/home/intake-foo")
        expected_result = [object1.copy()]
        expected_result[0]['duplicateOf'] = "/tempZone/home/intake-foo/1.dat"
        self.assertEqual(get_duplicates([object1], [object2]), expected_result)

    def test_get_duplicates_two_duplicates(self):
        object1 = self._get_test_object(dataobj="1.dat", checksum="123")
        object2 = self._get_test_object(dataobj="2.dat", checksum="456")
        object3 = self._get_test_object(dataobj="2.dat", checksum="456", coll="/tempZone/home/intake-foo")
        object4 = self._get_test_object(dataobj="1.dat", checksum="123", coll="/tempZone/home/intake-foo")
        expected_result = [object1.copy(), object2.copy()]
        expected_result[0]['duplicateOf'] = "/tempZone/home/intake-foo/1.dat"
        expected_result[1]['duplicateOf'] = "/tempZone/home/intake-foo/2.dat"
        self.assertEqual(sorted(get_duplicates([object1, object2], [object3, object4]), key=str),
                         sorted(expected_result, key=str))

    def _get_test_object(self, group="research-foo", coll="/tempZone/home/research-foo", dataobj="data.dat", checksum="123", size=456):
        return {'group': group,
                'parent': coll,
                'dataobj': dataobj,
                'chksum': checksum,
                'size': size
                }
