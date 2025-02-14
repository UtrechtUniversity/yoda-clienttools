# -*- coding: utf-8 -*-

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from unittest import makeSuite, TestSuite

from test_importgroups import ImportGroupsTest
from test_yoda_names import YodaNamesTest


def suite():
    test_suite = TestSuite()
    test_suite.addTest(makeSuite(ImportGroupsTest))
    test_suite.addTest(makeSuite(YodaNamesTest))
    return test_suite
