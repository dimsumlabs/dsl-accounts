
""" Perform tests on the balance.py
"""

import unittest
import datetime

import balance


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
        self.assertEqual(self.rows[0].month(), "1970-01")

    def test_hashtag(self):
        self.assertEqual(self.rows[0].hashtag(), None)

        self.assertEqual(self.rows[3].hashtag(), 'hashtag')

        obj = balance.Row("100", "1970-01-01", "#two #hashtags", "incoming")
        with self.assertRaises(ValueError):
            obj.hashtag()

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

        # feb is special - I just assume no years are leap years - show this
        self.assertEqual(r._month_add(date, -3), datetime.date(1970, 2, 28))
        self.assertEqual(r._month_add(date, 21), datetime.date(1972, 2, 28))

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
            datetime.date(1972, 2, 28),
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
            balance.Row("25", "1972-02-28", "!months:4 !child", "incoming"),
            balance.Row("25", "1972-03-31", "!months:4 !child", "incoming"),
            balance.Row("25", "1972-04-30", "!months:4 !child", "incoming"),
        ])

        # showing the rounding and kept remainder
        self.assertEqual(self.rows[6].autosplit(), [
            balance.Row("34", "1970-01-05", "!months:3 !child", "incoming"),
            balance.Row("33", "1970-02-05", "!months:3 !child", "incoming"),
            balance.Row("33", "1970-03-05", "!months:3 !child", "incoming"),
        ])

    def test_match(self):
        obj = self.rows[2]
        with self.assertRaises(AttributeError):
            obj.match(foo='blah')

        self.assertEqual(obj.match(direction='flubber'), None)
        self.assertEqual(obj.match(comment='a !bangtag'), obj)
        self.assertEqual(obj.match(month='1970-01'), obj)


class TestMisc(unittest.TestCase):
    def setUp(self):
        r = [None for x in range(6)]
        r[0] = balance.Row("10", "1970-02-06", "comment4", "outgoing")
        r[1] = balance.Row("10", "1970-01-05", "comment1", "incoming")
        r[2] = balance.Row("10", "1970-01-10", "comment2 #rent", "outgoing")
        r[3] = balance.Row("10", "1970-01-01", "comment3 #water", "outgoing")
        r[4] = balance.Row("10", "1970-03-01", "comment5 #rent", "outgoing")
        r[5] = balance.Row("15", "1970-01-11", "comment6 #water", "outgoing")
        self.rows = r

    def tearDown(self):
        self.rows = None

    def test_apply_filter_strings(self):
        self.assertEqual(
            list(balance.apply_filter_strings(
                    ["comment=comment1", "month=1970-01"],
                    self.rows)),
            self.rows[1:2]
        )

        self.assertEqual(
            list(balance.apply_filter_strings(None, self.rows)),
            self.rows
        )

        with self.assertRaises(ValueError):
            list(balance.apply_filter_strings(['noequalsignhere'], self.rows))

    def test_grid_accumulate(self):
        self.assertEqual(
            balance.grid_accumulate(self.rows), (
                set(['1970-03', '1970-02', '1970-01']),
                set(['Out water', 'Out unknown', 'Out rent', 'In unknown']),
                {
                    'Out water': {
                        '1970-01': {
                            'sum': -25,
                            'last': datetime.date(1970, 1, 11)
                        }
                    },
                    'Out unknown': {
                        '1970-02': {
                            'sum': -10,
                            'last': datetime.date(1970, 2, 6)
                        }
                    },
                    'Out rent': {
                        '1970-03': {
                            'sum': -10,
                            'last': datetime.date(1970, 3, 1)
                        },
                        '1970-01': {
                            'sum': -10,
                            'last': datetime.date(1970, 1, 10)
                        }
                    },
                    'In unknown': {
                        '1970-01': {
                            'sum': 10,
                            'last': datetime.date(1970, 1, 5)
                        }
                    }
                },
                {
                    '1970-03': -10,
                    '1970-02': -10,
                    '1970-01': -25,
                    'total': -45
                }))

    def test_topay_render(self):
        strings = {
            'header': 'header: {date}',
            'table_start': 'table_start:',
            'table_end': 'table_end:',
            'table_row': 'table_row: {hashtag}, {price}, {date}',
        }

        self.assertEqual(
            balance.topay_render(self.rows, strings),
            """header: 1970-01
table_start:
table_row: Out rent, -10, 1970-01-10
table_row: Out unknown, $0, Not Yet
table_row: Out water, -25, 1970-01-11
table_end:
header: 1970-02
table_start:
table_row: Out rent, $0, Not Yet
table_row: Out unknown, -10, 1970-02-06
table_row: Out water, $0, Not Yet
table_end:
header: 1970-03
table_start:
table_row: Out rent, -10, 1970-03-01
table_row: Out unknown, $0, Not Yet
table_row: Out water, $0, Not Yet
table_end:
"""
        )

    def test_grid_render(self):
        expect = ""
        expect += "               1970-01   1970-02   1970-03\n"
        expect += "In unknown          10                    \n"
        expect += "Out rent           -10                 -10\n"
        expect += "Out unknown                  -10          \n"
        expect += "Out water          -25                    \n"
        expect += "\n"
        expect += "TOTALS             -25       -10       -10\n"
        expect += "TOTAL:        -45"

        (m, t, grid, total) = balance.grid_accumulate(self.rows)
        self.assertEqual(balance.grid_render(m, t, grid, total), expect)
