
""" Perform tests on the balance.py
"""

import unittest
import datetime
import sys
import os

# Ensure that we look for any modules in our local lib dir.  This allows simple
# testing and development use.  It also does not break the case where the lib
# has been installed properly on the normal sys.path
sys.path.insert(0,
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
                )
# I would use site.addsitedir, but it does an append, not insert

import rowset as balance # noqa


class TestRowSet(unittest.TestCase):
    def setUp(self):
        r = [None for x in range(6)]
        r[0] = balance.Row("-10", "1970-02-06", "comment4") # noqa
        r[1] = balance.Row( "10", "1970-01-05", "comment1") # noqa
        r[2] = balance.Row("-10", "1970-01-10", "comment2 #rent") # noqa
        r[3] = balance.Row("-10", "1970-01-01", "comment3 #water") # noqa
        r[4] = balance.Row("-10", "1970-03-01", "comment5 #rent") # noqa
        r[5] = balance.Row("-15", "1970-01-11", "comment6 #water !months:3") # noqa
        self.rows_array = r

        self.rows = balance.RowSet()

    def tearDown(self):
        self.rows_array = None
        self.rows = None

    def test_value(self):
        self.rows.append(self.rows_array)

        self.assertEqual(self.rows.value, -45)

        self.rows.append(balance.Row("-0.5", "1970-03-12", "comment9")) # noqa
        self.rows.append(balance.Row("-0.5", "1970-03-13", "comment10")) # noqa
        self.assertEqual(str(self.rows.value), '-46')

    def test_nested_rowset(self):
        self.rows.append(self.rows_array)

        r = [None for x in range(2)]
        r[0] = balance.Row("-13", "1971-02-06", "comment7") # noqa
        r[1] = balance.Row( "12", "1971-01-05", "comment8") # noqa
        self.rows.append(r)

        self.assertEqual(self.rows.value, -46)

    def test_append(self):
        self.rows.append(self.rows_array[0])

        # FIXME - looking inside the object
        self.assertEqual(len(self.rows.rows), 1)

        self.rows.append(self.rows_array)

        # FIXME - looking inside the object
        self.assertEqual(len(self.rows.rows), 7)

        # FIXME - test appending a generator

        with self.assertRaises(ValueError):
            self.rows.append(None)

    def test_filter(self):
        self.rows.append(self.rows_array)

        self.assertEqual(
            # FIXME - looking inside the object
            self.rows.filter(["comment==comment1", "month==1970-01"]).rows,
            self.rows_array[1:2]
        )

        self.assertEqual(
            # FIXME - looking inside the object
            self.rows.filter(None).rows,
            self.rows_array
        )

    def test_autosplit(self):
        self.rows.append(self.rows_array)

        # FIXME - looking inside the object
        self.assertEqual(len(self.rows.autosplit().rows), 8)

    def test_group_by(self):
        self.rows.append(self.rows_array)

        # TODO - should construct the expected dict and all its rows and
        # compare to that
        self.assertEqual(
            sorted(self.rows.group_by('month').keys()),
            [
                datetime.date(1970, 1, 1),
                datetime.date(1970, 2, 1),
                datetime.date(1970, 3, 1),
            ]
        )

        # TODO - should construct the expected dict and all its rows and
        # compare to that
        self.assertEqual(
            sorted(self.rows.group_by('hashtag').keys()),
            [
                'rent',
                'unknown',
                'water',
            ]
        )
