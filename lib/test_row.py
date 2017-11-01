
""" Perform tests on the balance.py
"""

import unittest
import datetime
import sys
import os
import json
if sys.version_info[0] == 2:  # pragma: no cover
    import mock
else:
    from unittest import mock  # pragma: no cover

# Ensure that we look for any modules in our local lib dir.  This allows simple
# testing and development use.  It also does not break the case where the lib
# has been installed properly on the normal sys.path
sys.path.insert(0,
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
                )
# I would use site.addsitedir, but it does an append, not insert

import row as balance
# Originally, this class was imported from the balance.py, thus the
# name in the import above
# TODO:
# - rename all the balance lines below to use row instead

class fakedatetime(datetime.datetime):

    @classmethod
    def now(cls):
        return cls(1990, 5, 4, 12, 12, 12, 0)


class TestRowClass(unittest.TestCase):
    def setUp(self):
        r = [None for x in range(7)]
        r[0] = balance.Row("100", "1970-01-01", "incoming comment", "incoming")
        r[1] = balance.Row("100", "1970-01-02", "outgoing comment", "outgoing")
        r[2] = balance.Row( "10", "1970-01-03", "a !bangtag", "incoming") # noqa
        r[3] = balance.Row("100", "1970-01-04", "a #hashtag", "incoming")
        r[4] = balance.Row("100", "1972-02-29", "!months:-1:5", "incoming")
        r[5] = balance.Row("100", "1972-01-31", "!months:4", "incoming")
        r[6] = balance.Row("100", "1970-01-05", "!months:3", "incoming")
        self.rows = r

    def tearDown(self):
        self.rows = None

    def test_direction(self):
        with self.assertRaises(ValueError):
            balance.Row("100", "1970-01-01", "a comment", "fred")

        self.assertEqual(
            balance.Row("100", "1970-01-01", "a comment", "signed").value,
            100
        )
        self.assertEqual(
            balance.Row("-100", "1970-01-01", "a comment", "signed").value,
            -100
        )

    def test_value(self):
        with self.assertRaises(ValueError):
            balance.Row("-100", "1970-01-01", "a comment", "incoming")

    def test_incoming(self):
        obj = self.rows[0]
        self.assertEqual(obj.value, 100)
        self.assertEqual(obj.comment, "incoming comment")
        self.assertEqual(obj.date, datetime.date(1970, 1, 1))
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
        self.assertEqual(self.rows[0].month, "1970-01")

    def test_hashtag(self):
        self.assertEqual(self.rows[0].hashtag, None)

        self.assertEqual(self.rows[3].hashtag, 'hashtag')

        with self.assertRaises(ValueError):
            balance.Row("100", "1970-01-01", "#two #hashtags", "incoming")

    def test_bangtag(self):
        self.assertEqual(self.rows[0].bangtag(), None)

        self.assertEqual(self.rows[2].bangtag(), 'bangtag')

        obj = balance.Row("100", "1970-01-01", "!two !bangtags", "incoming")
        with self.assertRaises(ValueError):
            obj.bangtag()

    def test__month_add(self):
        """I dont really want to test month maths, but I wrote it, so
        """
        r = self.rows[0]  # throw away to get to the namespace with _month_add
        date = datetime.date(1970, 5, 18)
        # simple add and subtract
        self.assertEqual(r._month_add(date, 0), date)
        self.assertEqual(r._month_add(date, 1), datetime.date(1970, 6, 18))
        self.assertEqual(r._month_add(date, -1), datetime.date(1970, 4, 18))

        # not crossing a year
        self.assertEqual(r._month_add(date, 7), datetime.date(1970, 12, 18))
        self.assertEqual(r._month_add(date, -4), datetime.date(1970, 1, 18))

        # crossing a year
        self.assertEqual(r._month_add(date, 8), datetime.date(1971, 1, 18))
        self.assertEqual(r._month_add(date, -5), datetime.date(1969, 12, 18))

        # silly large numbers
        self.assertEqual(r._month_add(date, 500), datetime.date(2012, 1, 18))
        self.assertEqual(r._month_add(date, -500), datetime.date(1928, 9, 18))

        # dates that dont exist in other months
        date = datetime.date(1970, 5, 31)
        self.assertEqual(r._month_add(date, 1), datetime.date(1970, 6, 30))
        self.assertEqual(r._month_add(date, -1), datetime.date(1970, 4, 30))

        # Show that leap years work
        self.assertEqual(r._month_add(date, -3), datetime.date(1970, 2, 28))
        self.assertEqual(r._month_add(date, 21), datetime.date(1972, 2, 29))

        # unless you ask for a zero increment, when the date is unchanged
        date = datetime.date(1972, 2, 29)
        self.assertEqual(r._month_add(date, 0), datetime.date(1972, 2, 29))

    def test__split_dates(self):
        self.assertEqual(self.rows[0]._split_dates(),
                         [datetime.date(1970, 1, 1)])
        self.assertEqual(self.rows[2]._split_dates(),
                         [datetime.date(1970, 1, 3)])
        self.assertEqual(self.rows[4]._split_dates(), [
            datetime.date(1972, 1, 29),
            datetime.date(1972, 2, 29),
            datetime.date(1972, 3, 29),
            datetime.date(1972, 4, 29),
            datetime.date(1972, 5, 29)
        ])
        self.assertEqual(self.rows[5]._split_dates(), [
            datetime.date(1972, 1, 31),
            datetime.date(1972, 2, 29),
            datetime.date(1972, 3, 31),
            datetime.date(1972, 4, 30),
        ])

        obj = balance.Row("100", "1970-01-01", "!months", "incoming")
        with self.assertRaises(ValueError):
            obj._split_dates()
        obj = balance.Row("100", "1970-01-01", "!months:1:2:3", "incoming")
        with self.assertRaises(ValueError):
            obj._split_dates()

    def test_autosplit(self):
        self.assertEqual(self.rows[0].autosplit(), [self.rows[0]])

        # showing we can have a leap day if it is the original row date
        self.assertEqual(self.rows[4].autosplit(), [
            balance.Row("20", "1972-01-29", "!months:-1:5 !child", "incoming"),
            balance.Row("20", "1972-02-29", "!months:-1:5 !child", "incoming"),
            balance.Row("20", "1972-03-29", "!months:-1:5 !child", "incoming"),
            balance.Row("20", "1972-04-29", "!months:-1:5 !child", "incoming"),
            balance.Row("20", "1972-05-29", "!months:-1:5 !child", "incoming"),
        ])

        # showing the end of month clamping to different values
        self.assertEqual(self.rows[5].autosplit(), [
            balance.Row("25", "1972-01-31", "!months:4 !child", "incoming"),
            balance.Row("25", "1972-02-29", "!months:4 !child", "incoming"),
            balance.Row("25", "1972-03-31", "!months:4 !child", "incoming"),
            balance.Row("25", "1972-04-30", "!months:4 !child", "incoming"),
        ])

        # showing the rounding and kept remainder
        self.assertEqual(self.rows[6].autosplit(), [
            balance.Row("34", "1970-01-05", "!months:3 !child", "incoming"),
            balance.Row("33", "1970-02-05", "!months:3 !child", "incoming"),
            balance.Row("33", "1970-03-05", "!months:3 !child", "incoming"),
        ])

        # TODO - at at least a trivial example showing method==proportional

    def test_match(self):
        obj = self.rows[2]
        with self.assertRaises(AttributeError):
            obj.match(foo='blah')

        self.assertEqual(obj.match(direction='flubber'), None)
        self.assertEqual(obj.match(comment='a !bangtag'), obj)
        self.assertEqual(obj.match(month='1970-01'), obj)

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

    @mock.patch('balance.datetime.datetime', fakedatetime)
    def test_filter_rel_months(self):
        obj = self.rows[2]
        self.assertEqual(obj.filter('rel_months<-264'), obj)
        self.assertEqual(obj.filter('rel_months<-265'), None)


