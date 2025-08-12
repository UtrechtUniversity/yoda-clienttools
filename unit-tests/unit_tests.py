# -*- coding: utf-8 -*-

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from unittest import TestSuite

from test_importgroups import ImportGroupsTest
from test_reportoldvsnewdata import OldNewDataReportTest
from test_yoda_names import YodaNamesTest


def suite():
    test_suite = TestSuite()
    test_suite.addTest(ImportGroupsTest)
    # test_suite.addTest(ExportGroupsTest)
    test_suite.addTest(OldNewDataReportTest)
    test_suite.addTest(YodaNamesTest)
    return test_suite
