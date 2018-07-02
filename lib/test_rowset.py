
""" Perform tests on the balance.py
"""

import unittest
import datetime
import sys
import os

try:
    # python 2
    from StringIO import StringIO
except ImportError:
    # python 3
    from io import StringIO

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
        f = StringIO("""
# Files can contain comments and empty lines

-10 1970-02-06 comment4
10 1970-01-05 comment1
-10 1970-01-10 comment2 #rent
-10 1970-01-01 comment3 #water
-10 1970-03-01 comment5 #rent
-15 1970-01-11 comment6 #water !months:3
""")
        self.rows = balance.RowSet()
        self.rows.load_file(f)

    def tearDown(self):
        self.rows = None

    def test_value(self):
        self.assertEqual(self.rows.value, -45)

        self.rows.append(balance.Row("-0.5", "1970-03-12", "comment9")) # noqa
        self.rows.append(balance.Row("-0.5", "1970-03-13", "comment10")) # noqa
        self.assertEqual(str(self.rows.value), '-46')

    def test_nested_rowset(self):
        r = [None for x in range(2)]
        r[0] = balance.Row("-13", "1971-02-06", "comment7") # noqa
        r[1] = balance.Row( "12", "1971-01-05", "comment8") # noqa
        self.rows.append(r)

        self.assertEqual(self.rows.value, -46)

    def test_append(self):
        # FIXME - looking inside the object
        self.assertEqual(len(self.rows.rows), 6)

        row = self.rows.rows[0]
        self.rows.append(row)

        # FIXME - looking inside the object
        self.assertEqual(len(self.rows.rows), 7)

        # FIXME - test appending a generator

        with self.assertRaises(ValueError):
            self.rows.append(None)

    def test_filter(self):
        rows = self.rows.rows[1:2]

        self.assertEqual(
            # FIXME - looking inside the object
            self.rows.filter(["comment==comment1", "month==1970-01"]).rows,
            rows
        )

        rows = self.rows.rows

        self.assertEqual(
            # FIXME - looking inside the object
            self.rows.filter(None).rows,
            rows
        )

    def test_autosplit(self):
        # FIXME - looking inside the object
        self.assertEqual(len(self.rows.autosplit().rows), 8)

    def test_group_by(self):
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

    def test_save_file(self):
        expect = [
            '-10 1970-02-06 comment4',
            '10 1970-01-05 comment1',
            '-10 1970-01-10 comment2 #rent',
            '-10 1970-01-01 comment3 #water',
            '-10 1970-03-01 comment5 #rent',
            '-15 1970-01-11 comment6 #water !months:3',
            ''
        ]

        f = StringIO()
        self.rows.save_file(f)
        got = f.getvalue().split("\n")

        self.assertEqual(got, expect)
