# -*- coding: utf-8 -*-

"""Unit tests for old vs. new data report
"""

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append("../yclienttools")

from reportoldvsnewdata import aggregate_by_category  # type: ignore[import-not-found]


class OldNewDataReportTest(TestCase):
    def test_aggregate_no_groups(self):
        inputdata = []
        self.assertEqual(aggregate_by_category(inputdata, None), [])

    def test_aggregate_single_group(self):
        group1 = {"Category": "testcategory",
                  "Subcategory": "testsubcategory",
                  "Group name":  "research-group1",
                  "Research collection size (both)": 3,
                  "Vault collection size (both)": 6,
                  "Revisions size (both)": 8,
                  "Total size (both)": 17,
                  "Research collection size (old data)": 2,
                  "Vault collection size (old data)": 3,
                  "Revisions size (old data)": 4,
                  "Total size (old data)": 9,
                  "Research collection size (new data)": 1,
                  "Vault collection size (new data)": 3,
                  "Revisions size (new data)": 4,
                  "Total size (new data)": 8
                  }
        expected_output1 = {"Category": "testcategory",
                            "Subcategory": "all",
                            "Group name":  "all",
                            "Research collection size (both)": 3,
                            "Vault collection size (both)": 6,
                            "Revisions size (both)": 8,
                            "Total size (both)": 17,
                            "Research collection size (old data)": 2,
                            "Vault collection size (old data)": 3,
                            "Revisions size (old data)": 4,
                            "Total size (old data)": 9,
                            "Research collection size (new data)": 1,
                            "Vault collection size (new data)": 3,
                            "Revisions size (new data)": 4,
                            "Total size (new data)": 8
                            }
        output = aggregate_by_category([group1], None)
        self.assertEqual(len(output), 1)
        self.assertDictEqual(output[0], expected_output1)

    def test_aggregate_two_groups_same_category(self):
        group1 = {"Category": "testcategory",
                  "Subcategory": "testsubcategory",
                  "Group name":  "research-group1",
                  "Research collection size (both)": 3,
                  "Vault collection size (both)": 6,
                  "Revisions size (both)": 8,
                  "Total size (both)": 17,
                  "Research collection size (old data)": 2,
                  "Vault collection size (old data)": 3,
                  "Revisions size (old data)": 4,
                  "Total size (old data)": 9,
                  "Research collection size (new data)": 1,
                  "Vault collection size (new data)": 3,
                  "Revisions size (new data)": 4,
                  "Total size (new data)": 8
                  }
        group2 = {"Category": "testcategory",
                  "Subcategory": "testsubcategory",
                  "Group name":  "research-group2",
                  "Research collection size (both)": 3,
                  "Vault collection size (both)": 6,
                  "Revisions size (both)": 8,
                  "Total size (both)": 17,
                  "Research collection size (old data)": 2,
                  "Vault collection size (old data)": 3,
                  "Revisions size (old data)": 4,
                  "Total size (old data)": 9,
                  "Research collection size (new data)": 1,
                  "Vault collection size (new data)": 3,
                  "Revisions size (new data)": 4,
                  "Total size (new data)": 8
                  }
        expected_output1 = {"Category": "testcategory",
                            "Subcategory": "all",
                            "Group name":  "all",
                            "Research collection size (both)": 6,
                            "Vault collection size (both)": 12,
                            "Revisions size (both)": 16,
                            "Total size (both)": 34,
                            "Research collection size (old data)": 4,
                            "Vault collection size (old data)": 6,
                            "Revisions size (old data)": 8,
                            "Total size (old data)": 18,
                            "Research collection size (new data)": 2,
                            "Vault collection size (new data)": 6,
                            "Revisions size (new data)": 8,
                            "Total size (new data)": 16
                            }
        output = aggregate_by_category([group1, group2], None)
        self.assertEqual(len(output), 1)
        self.assertDictEqual(output[0], expected_output1)

    def test_aggregate_two_groups_different_category(self):
        group1 = {"Category": "testcategory1",
                  "Subcategory": "testsubcategory",
                  "Group name":  "research-group1",
                  "Research collection size (both)": 3,
                  "Vault collection size (both)": 6,
                  "Revisions size (both)": 8,
                  "Total size (both)": 17,
                  "Research collection size (old data)": 2,
                  "Vault collection size (old data)": 3,
                  "Revisions size (old data)": 4,
                  "Total size (old data)": 9,
                  "Research collection size (new data)": 1,
                  "Vault collection size (new data)": 3,
                  "Revisions size (new data)": 4,
                  "Total size (new data)": 8
                  }
        group2 = {"Category": "testcategory2",
                  "Subcategory": "testsubcategory",
                  "Group name":  "research-group2",
                  "Research collection size (both)": 3,
                  "Vault collection size (both)": 6,
                  "Revisions size (both)": 8,
                  "Total size (both)": 17,
                  "Research collection size (old data)": 2,
                  "Vault collection size (old data)": 3,
                  "Revisions size (old data)": 4,
                  "Total size (old data)": 9,
                  "Research collection size (new data)": 1,
                  "Vault collection size (new data)": 3,
                  "Revisions size (new data)": 4,
                  "Total size (new data)": 8
                  }
        expected_output1 = {"Category": "testcategory1",
                            "Subcategory": "all",
                            "Group name":  "all",
                            "Research collection size (both)": 3,
                            "Vault collection size (both)": 6,
                            "Revisions size (both)": 8,
                            "Total size (both)": 17,
                            "Research collection size (old data)": 2,
                            "Vault collection size (old data)": 3,
                            "Revisions size (old data)": 4,
                            "Total size (old data)": 9,
                            "Research collection size (new data)": 1,
                            "Vault collection size (new data)": 3,
                            "Revisions size (new data)": 4,
                            "Total size (new data)": 8
                            }
        expected_output2 = {"Category": "testcategory2",
                            "Subcategory": "all",
                            "Group name":  "all",
                            "Research collection size (both)": 3,
                            "Vault collection size (both)": 6,
                            "Revisions size (both)": 8,
                            "Total size (both)": 17,
                            "Research collection size (old data)": 2,
                            "Vault collection size (old data)": 3,
                            "Revisions size (old data)": 4,
                            "Total size (old data)": 9,
                            "Research collection size (new data)": 1,
                            "Vault collection size (new data)": 3,
                            "Revisions size (new data)": 4,
                            "Total size (new data)": 8
                            }
        output = aggregate_by_category([group1, group2], None)
        self.assertEqual(len(output), 2)
        self.assertDictEqual(output[0], expected_output1)
        self.assertDictEqual(output[1], expected_output2)
