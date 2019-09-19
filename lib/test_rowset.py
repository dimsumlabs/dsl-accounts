
""" Perform tests on the rowset.py
"""

import unittest
import datetime
import sys
import os

from datetime import date as Date

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

import rowset # noqa
import row

class TestRowSet(unittest.TestCase):
    def setUp(self):
        f = StringIO("""
# Files can contain comments and empty lines

#balance 0 Opening Balance
-10 1970-02-06 comment4
10 1970-01-05 comment1
-10 1970-01-10 comment2 #bills:rent
-10 1970-01-01 comment3 #bills:water
-10 1970-03-01 comment5 #bills:rent
-15 1970-01-11 comment6 #bills:water !months:3
#balance -45 A comment
""")
        self.rows = rowset.RowSet()
        self.rows.load_file(f)

    def tearDown(self):
        self.rows = None

    def test_value(self):
        self.assertEqual(self.rows.value, -45)

        self.rows.append(row.Row("-0.5", Date(1970,03,12), "comment9")) # noqa
        self.rows.append(row.Row("-0.5", Date(1970,03,13), "comment10")) # noqa
        self.assertEqual(str(self.rows.value), '-46')

    def test_load_file1(self):
        """Loading a file into an existing rowset requires a balance pragma
        """

        with self.assertRaises(ValueError):
            self.rows.load_file(StringIO('10 1970-03-20 comment12'))

        f = StringIO("""
# First non transaction line is a balance line

#balance -45 comment 13
10 1970-03-20 comment14
""")
        self.rows.load_file(f)

    def test_load_file2(self):
        """Special files can be loaded with the balance check skipped
        """

        self.rows.load_file(
            StringIO('10 1970-03-20 comment12'),
            skip_balance_check=True
        )

    def test_load_file3(self):
        """Any balance pragma must match the running balance
        """

        f = StringIO("""
10 1972-02-03 comment7
#balance 100000 The wrong balance
""")

        set = rowset.RowSet()
        with self.assertRaises(ValueError):
            set.load_file(f)

# TODO: loading a file with a syntax error should raise an exception

    def test_nested_rowset(self):
        r = [None for x in range(2)]
        r[0] = row.Row("-13", Date(1971,02,06), "comment7") # noqa
        r[1] = row.Row( "12", Date(1971,01,05), "comment8") # noqa
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
                Date(1970, 1, 1),
                Date(1970, 2, 1),
                Date(1970, 3, 1),
            ]
        )

        # TODO - should construct the expected dict and all its rows and
        # compare to that
        self.assertEqual(
            sorted(self.rows.group_by('hashtag').keys()),
            [
                'bills:rent',
                'bills:water',
                'unknown',
            ]
        )

    def test_save_file(self):
        expect = [
            '-10 1970-02-06 comment4',
            '10 1970-01-05 comment1',
            '-10 1970-01-10 comment2 #bills:rent',
            '-10 1970-01-01 comment3 #bills:water',
            '-10 1970-03-01 comment5 #bills:rent',
            '-15 1970-01-11 comment6 #bills:water !months:3',
            ''
        ]

        f = StringIO()
        self.rows.save_file(f)
        got = f.getvalue().split("\n")

        self.assertEqual(got, expect)
