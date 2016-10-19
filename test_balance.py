
""" Perform tests on the balance.py
"""

import unittest
import datetime

import balance


class TestRowClass(unittest.TestCase):
    def setUp(self):
        r = [None for x in range(4)]
        r[0] = balance.Row("100", "1970-01-01", "incoming comment", "incoming")
        r[1] = balance.Row("100", "1970-01-02", "outgoing comment", "outgoing")
        r[2] = balance.Row( "10", "1970-01-03", "a comment3", "incoming") # noqa
        r[3] = balance.Row("100", "1970-01-04", "a #hashtag", "incoming")
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
        self.assertEqual(obj.date, datetime.datetime(1970, 1, 1, 0, 0))
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

    def test_match(self):
        obj = self.rows[2]
        with self.assertRaises(AttributeError):
            obj.match(foo='blah')

        self.assertEqual(obj.match(direction='flubber'), None)
        self.assertEqual(obj.match(comment='a comment3'), obj)
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

    def test_grid_accumulate(self):
        self.assertEqual(
            balance.grid_accumulate(self.rows),(
                set(['1970-03', '1970-02', '1970-01']),
                set(['Out water', 'Out unknown', 'Out rent', 'In unknown']),
                {
                    'Out water': {
                        '1970-01': {
                            'sum': -25,
                            'last': datetime.datetime(1970, 1, 11, 0, 0)
                        }
                    },
                    'Out unknown': {
                        '1970-02': {
                            'sum': -10,
                            'last': datetime.datetime(1970, 2, 6, 0, 0)
                        }
                    },
                    'Out rent': {
                        '1970-03': {
                            'sum': -10,
                            'last': datetime.datetime(1970, 3, 1, 0, 0)
                        },
                        '1970-01': {
                            'sum': -10,
                            'last': datetime.datetime(1970, 1, 10, 0, 0)
                        }
                    },
                    'In unknown': {
                        '1970-01': {
                            'sum': 10,
                            'last': datetime.datetime(1970, 1, 5, 0, 0)
                        }
                    }
                },
                {
                    '1970-03': -10,
                    '1970-02': -10,
                    '1970-01': -25,
                    'total': -45
                }
        ) )

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
table_row: Out rent, -10, 1970-01-10 00:00:00
table_row: Out unknown, $0, Not Yet
table_row: Out water, -25, 1970-01-11 00:00:00
table_end:
header: 1970-02
table_start:
table_row: Out rent, $0, Not Yet
table_row: Out unknown, -10, 1970-02-06 00:00:00
table_row: Out water, $0, Not Yet
table_end:
header: 1970-03
table_start:
table_row: Out rent, -10, 1970-03-01 00:00:00
table_row: Out unknown, $0, Not Yet
table_row: Out water, $0, Not Yet
table_end:
"""
        )

    def test_grid_render(self):
        expect = ""
        expect += "           	1970-01	1970-02	1970-03	\n"
        expect += "In unknown 	     10			\n"
        expect += "Out rent   	    -10		    -10	\n"
        expect += "Out unknown		    -10		\n"
        expect += "Out water  	    -25			\n"
        expect += "\n"
        expect += "TOTALS     	    -25	    -10	    -10	\n"
        expect += "TOTAL:	    -45"

        (m, t, grid, total) = balance.grid_accumulate(self.rows)
        self.assertEqual(balance.grid_render(m, t, grid, total), expect)
