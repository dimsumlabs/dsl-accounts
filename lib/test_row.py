
""" Perform tests on the row.py
"""

import unittest
import datetime
from datetime import date as Date
import sys
import os
from unittest import mock  # pragma: no cover

# Ensure that we look for any modules in our local lib dir.  This allows simple
# testing and development use.  It also does not break the case where the lib
# has been installed properly on the normal sys.path
sys.path.insert(0,
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
                )
# I would use site.addsitedir, but it does an append, not insert

import row # noqa


class fakedatetime(datetime.datetime):

    @classmethod
    def now(cls):
        return cls(1990, 5, 4, 12, 12, 12, 0)


class TestRowClass(unittest.TestCase):
    def setUp(self):

        data = [
            "100  1970-01-01 incoming comment",
            "-100 1970-01-02 outgoing comment",
            "10   1970-01-03 a !test_bangtag",
            "100  1970-01-04 a #test_hashtag",
            "100  1972-02-29 !months:-1:5",
            "100  1972-01-31 !months:4",
            "100  1970-01-05 !months:3",
        ]

        r = []
        for line in data:
            r.append(row.Row.fromTxt(line))

        self.rows = r

    def tearDown(self):
        self.rows = None

    def test_incoming(self):
        obj = self.rows[0]
        self.assertEqual(obj.direction, 'incoming')

    def test_outgoing(self):
        obj = self.rows[1]
        self.assertEqual(obj.value, -100)
        self.assertEqual(obj.direction, 'outgoing')

    def test_addnum(self):
        self.assertEqual(self.rows[0]+10, 110)

    def test_raddnum(self):
        self.assertEqual(10+self.rows[0], 110)

    def test_addrow(self):
        self.assertEqual(self.rows[0] + self.rows[2], 110)

    def test_month(self):
        self.assertEqual(self.rows[0].month, Date(1970, 1, 1))

    def test_hashtag(self):
        self.assertEqual(self.rows[0].hashtag, None)

        self.assertEqual(self.rows[3].hashtag, 'test_hashtag')

        with self.assertRaises(ValueError):
            row.RowData("100", Date(1970, 1, 1), "#test_hashtag #test_hashtag2")

    def test_bangtag(self):
        self.assertEqual(self.rows[0].bangtag, dict())

        self.assertIn('test_bangtag', self.rows[2].bangtag)

        with self.assertRaises(ValueError):
            row.RowData("100", Date(1970, 1, 1), "!test_bangtag !test_bangtag")

    def test__month_add(self):
        """I dont really want to test month maths, but I wrote it, so
        """
        r = self.rows[0]  # throw away to get to the namespace with _month_add
        date = Date(1970, 5, 18)
        # simple add and subtract
        self.assertEqual(r._month_add(date, 0), date)
        self.assertEqual(r._month_add(date, 1), Date(1970, 6, 18))
        self.assertEqual(r._month_add(date, -1), Date(1970, 4, 18))

        # not crossing a year
        self.assertEqual(r._month_add(date, 7), Date(1970, 12, 18))
        self.assertEqual(r._month_add(date, -4), Date(1970, 1, 18))

        # crossing a year
        self.assertEqual(r._month_add(date, 8), Date(1971, 1, 18))
        self.assertEqual(r._month_add(date, -5), Date(1969, 12, 18))

        # silly large numbers
        self.assertEqual(r._month_add(date, 500), Date(2012, 1, 18))
        self.assertEqual(r._month_add(date, -500), Date(1928, 9, 18))

        # dates that dont exist in other months
        date = Date(1970, 5, 31)
        self.assertEqual(r._month_add(date, 1), Date(1970, 6, 30))
        self.assertEqual(r._month_add(date, -1), Date(1970, 4, 30))

        # Show that leap years work
        self.assertEqual(r._month_add(date, -3), Date(1970, 2, 28))
        self.assertEqual(r._month_add(date, 21), Date(1972, 2, 29))

        # unless you ask for a zero increment, when the date is unchanged
        date = Date(1972, 2, 29)
        self.assertEqual(r._month_add(date, 0), Date(1972, 2, 29))

    def test__split_dates(self):
        self.assertEqual(self.rows[0]._split_dates(),
                         [Date(1970, 1, 1)])
        self.assertEqual(self.rows[2]._split_dates(),
                         [Date(1970, 1, 3)])
        self.assertEqual(self.rows[4]._split_dates(), [
            Date(1972, 1, 29),
            Date(1972, 2, 29),
            Date(1972, 3, 29),
            Date(1972, 4, 29),
            Date(1972, 5, 29)
        ])
        self.assertEqual(self.rows[5]._split_dates(), [
            Date(1972, 1, 31),
            Date(1972, 2, 29),
            Date(1972, 3, 31),
            Date(1972, 4, 30),
        ])

        with self.assertRaises(ValueError):
            row.RowData("100", Date(1970, 1, 1), "!months")
        with self.assertRaises(ValueError):
            row.RowData("100", Date(1970, 1, 1), "!months:1:2:3")

    def test_match(self):
        obj = self.rows[2]
        with self.assertRaises(AttributeError):
            obj.match(foo='blah')

        self.assertEqual(obj.match(direction='flubber'), None)
        self.assertEqual(obj.match(comment='a !test_bangtag'), obj)
        self.assertEqual(obj.match(month='1970-01-01'), obj)

    def test_filter(self):
        obj = self.rows[2]
        with self.assertRaises(ValueError):
            obj.filter('direction<>value')      # bad operator
        with self.assertRaises(ValueError):
            obj.filter('nooperator')

        self.assertEqual(obj.filter('date==1970-01-03'), obj)
        self.assertEqual(obj.filter('date==1970-01-05'), None)

        self.assertEqual(obj.filter('date!=1970-01-03'), None)
        self.assertEqual(obj.filter('date!=1970-01-05'), obj)

        self.assertEqual(obj.filter('date<1970-01-02'), None)
        self.assertEqual(obj.filter('date<1970-01-05'), obj)

        self.assertEqual(obj.filter('month>1969-12'), obj)
        self.assertEqual(obj.filter('month>1970-01'), None)

        self.assertEqual(obj.filter('comment=~gtag'), obj)
        self.assertEqual(obj.filter('comment=~^a'), obj)
        self.assertEqual(obj.filter('comment!~^a'), None)
        self.assertEqual(obj.filter('comment=~^foo'), None)
        self.assertEqual(obj.filter('comment!~^foo'), obj)

    @mock.patch('row.datetime.datetime', fakedatetime)
    def test_filter_rel_months(self):
        obj = self.rows[2]
        self.assertEqual(obj.filter('rel_months<-264'), obj)
        self.assertEqual(obj.filter('rel_months<-265'), None)

    def test_str(self):
        self.assertEqual(str(self.rows[4]), "100 1972-02-29 !months:-1:5")


class TestRowPragmaClass(unittest.TestCase):
    def test_balance(self):
        input_data = "#balance 10 The Comment"
        obj = row.Row.fromTxt(input_data)

        self.assertIsInstance(obj, row.RowPragmaBalance)
        self.assertEqual(obj.balance, 10)
        self.assertEqual(obj.comment, 'The Comment')
        self.assertEqual(str(obj), input_data)

        with self.assertRaises(ValueError):
            row.Row.fromTxt("#balance notanumber Still a Comment")

        with self.assertRaises(ValueError):
            row.RowPragma.fromTxt("No leading hash")


class TestRowDataClass(unittest.TestCase):
    def test_fields(self):
        obj = row.RowData(10, Date(1970, 10, 20), "A Comment")

        self.assertIsInstance(obj, row.RowData)
        self.assertEqual(obj.value, 10)
        self.assertEqual(obj.date, Date(1970, 10, 20))
        self.assertEqual(obj.comment, "A Comment")

        with self.assertRaises(ValueError):
            row.RowData(10, 'notadate', "A Comment")
