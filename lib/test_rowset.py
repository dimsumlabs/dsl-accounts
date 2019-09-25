
""" Perform tests on the rowset.py
"""

import unittest
import sys
import os
import decimal

from datetime import date as Date
from io import StringIO

# Ensure that we look for any modules in our local lib dir.  This allows simple
# testing and development use.  It also does not break the case where the lib
# has been installed properly on the normal sys.path
sys.path.insert(0,
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
                )
# I would use site.addsitedir, but it does an append, not insert

import rowset # noqa
import row # noqa


class TestRowSet(unittest.TestCase):
    input_data = """
# Files can contain comments and empty lines
#

#balance 0 Opening Balance
-10 1970-02-06 comment4
10 1970-01-05 comment1
-10 1970-01-10 comment2 #bills:rent
-10 1970-01-01 comment3 #bills:water
-10 1970-03-01 comment5 #bills:rent
-15 1970-01-11 comment6 #bills:water !months:3
#balance -45
"""

    def setUp(self):
        f = StringIO(self.input_data)
        self.rows = rowset.RowSet()
        self.rows.load_file(f)

    def tearDown(self):
        self.rows = None

    def test_str(self):
        self.assertEqual(str(self.rows), self.input_data)

    def test_value(self):
        self.assertEqual(self.rows.value, -45)

        self.rows.append(row.RowData("-0.5", Date(1970, 3,12), "comment9")) # noqa
        self.rows.append(row.RowData("-0.5", Date(1970, 3,13), "comment10")) # noqa
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

    def test_load_file4(self):
        """Loading a file with a mismatching balance will cause error
        """

        f = StringIO("""
# First non transaction line is a balance line

#balance -50 comment 23
10 1970-03-20 comment24
""")
        with self.assertRaises(ValueError):
            self.rows.load_file(f)

    def test_load_file5(self):
        """Loading a file with a syntax error will cause error
        """

        f = StringIO("""
apple 1970-03-20 comment24
""")
        with self.assertRaises(decimal.InvalidOperation):
            self.rows.load_file(f)

# TODO: loading a file with a syntax error should raise an exception

    def test_nested_rowset(self):
        r = [None for x in range(2)]
        r[0] = row.RowData("-13", Date(1971, 2, 6), "comment7") # noqa
        r[1] = row.RowData( "12", Date(1971, 1, 5), "comment8") # noqa
        self.rows.append(r)

        self.assertEqual(self.rows.value, -46)

    def test_append(self):
        # FIXME - looking inside the object
        self.assertEqual(len(self.rows.rows), 12)

        row = self.rows.rows[3]
        self.rows.append(row)

        # FIXME - looking inside the object
        self.assertEqual(len(self.rows.rows), 13)

        # FIXME - test appending a generator

        with self.assertRaises(ValueError):
            self.rows.append(None)

    def test_filter(self):
        rows = self.rows.rows[6:7]

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


class TestAutoSplit(unittest.TestCase):

    def test_len(self):
        """After splitting, we should have the right number of new rows"""
        input_data = """
#balance 0
100  1980-01-01 incoming comment
-100 1980-01-02 outgoing comment
10   1980-01-03 a !test_bangtag
100  1980-01-04 a #test_hashtag
100  1984-02-29 !months:-1:5
100  1984-01-31 !months:4
100  1980-01-05 !months:3
"""
        rows = rowset.RowSet()
        rows.load_file(StringIO(input_data))

        self.assertEqual(len(rows), 9)
        self.assertEqual(len(rows.autosplit()), 18)

    def test_leapday(self):
        """We can split a leap day, if it is the original row date"""
        input_data = """
#balance 0
100  1984-02-29 !months:-1:5
"""
        rows = rowset.RowSet()
        rows.load_file(StringIO(input_data))

        got = str(rows.autosplit())

        expected = """
#balance 0
20 1984-01-29 !months:child
20 1984-02-29 !months:child
20 1984-03-29 !months:child
20 1984-04-29 !months:child
20 1984-05-29 !months:child
"""

        self.assertEqual(expected, got)

    def test_endofmonth(self):
        """When splitting, We clamp to the correct end of month"""
        input_data = """
#balance 0
100  1984-01-31 !months:4
"""
        rows = rowset.RowSet()
        rows.load_file(StringIO(input_data))

        got = str(rows.autosplit())

        expected = """
#balance 0
25 1984-01-31 !months:child
25 1984-02-29 !months:child
25 1984-03-31 !months:child
25 1984-04-30 !months:child
"""

        self.assertEqual(expected, got)

    def test_rounding(self):
        """When splitting, round down and add the remainder to the first"""
        input_data = """
#balance 0
100  1980-01-05 !months:3
"""
        rows = rowset.RowSet()
        rows.load_file(StringIO(input_data))

        got = str(rows.autosplit())

        expected = """
#balance 0
34 1980-01-05 !months:child
33 1980-02-05 !months:child
33 1980-03-05 !months:child
"""

        self.assertEqual(expected, got)
