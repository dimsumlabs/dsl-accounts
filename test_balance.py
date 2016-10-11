
""" Perform tests on the balance.py
"""

import unittest
import datetime

import balance

class TestRowClass(unittest.TestCase):

    def test_direction(self):
        with self.assertRaises(ValueError):
            object = balance.Row("100","1970-01-01","a comment","fred")

    def test_incoming(self):
        object = balance.Row("100","1970-01-01","a comment","incoming")
        self.assertEqual(object.value,100)
        self.assertEqual(object.comment,"a comment")
        self.assertEqual(object.date,datetime.datetime(1970, 1, 1, 0, 0))
        self.assertEqual(object.direction,'incoming')

    def test_outgoing(self):
        object = balance.Row("100","1970-01-01","a comment","outgoing")
        self.assertEqual(object.value,-100)
        self.assertEqual(object.direction,'outgoing')

    def test_addnum(self):
        object = balance.Row("100","1970-01-01","a comment","incoming")
        self.assertEqual(object+10,110)

    def test_raddnum(self):
        object = balance.Row("100","1970-01-01","a comment","incoming")
        self.assertEqual(10+object,110)

    def test_addrow(self):
        object1 = balance.Row("100","1970-01-01","a comment","incoming")
        object2 = balance.Row("10","1971-01-01","a comment2","incoming")
        object3 = object1 + object2
        self.assertEqual(object3,110)

    def test_month(self):
        object = balance.Row("100","1970-01-01","a comment","incoming")
        self.assertEqual(object.month(),"1970-01")

    def test_hashtag(self):
        object = balance.Row("100","1970-01-01","a comment","incoming")
        self.assertEqual(object.hashtag(),None)

        object = balance.Row("100","1970-01-01","a #hashtag","incoming")
        self.assertEqual(object.hashtag(),'hashtag')

        object = balance.Row("100","1970-01-01","#two #hashtags","incoming")
        with self.assertRaises(ValueError):
            object.hashtag()

    def test_match(self):
        object = balance.Row("100","1970-01-01","a comment","incoming")
        with self.assertRaises(AttributeError):
            object.match(foo='blah')

        self.assertEqual(object.match(direction='flubber'),None)
        self.assertEqual(object.match(comment='a comment'),object)

class TestMisc(unittest.TestCase):

    def test_hashtag(self):
        rows = []
        rows.append(balance.Row("100","1970-01-01","a comment","incoming"))
        rows.append(balance.Row("10","1971-01-01","a comment2","incoming"))

        # look for "fred" in the comments
        self.assertEqual(
            balance.find_hashtag("fred",rows),
            (False, '$0', 'Not yet')
        )

        rows.append(balance.Row("10","1971-01-01","here #fred is","incoming"))
        self.assertEqual(
            balance.find_hashtag("fred",rows),
            (True, -10, datetime.datetime(1971, 1, 1, 0, 0))
        )

    def test_filter_outgoing_payments(self):
        rows = []
        rows.append(balance.Row("10","1970-01-05","comment1","incoming"))
        rows.append(balance.Row("10","1970-01-10","comment2","outgoing"))
        rows.append(balance.Row("10","1970-01-01","comment3","outgoing"))
        rows.append(balance.Row("10","1970-02-06","comment4","outgoing"))

        self.assertEqual(
            balance.filter_outgoing_payments(rows,'1970-01'),
            [
                balance.Row('10','1970-01-01','comment3','outgoing'),
                balance.Row('10','1970-01-10','comment2','outgoing'),
            ]
        )

    def test_payment_months(self):
        rows = []
        rows.append(balance.Row("10","1970-04-08","comment5","outgoing"))
        rows.append(balance.Row("10","1970-03-02","comment6","incoming"))

        self.assertEqual(
            balance.get_payment_months(rows),
            [ '1970-03', '1970-04' ]
        )

    def test_topay_render(self):
        rows = []
        rows.append(balance.Row("10","1970-05-15","foo #rent","outgoing"))
        rows.append(balance.Row("10","1970-06-17","bah #water","outgoing"))

        strings = {
            'header': 'header: {date}',
            'table_start': 'table_start:',
            'table_end': 'table_end:',
            'table_row': 'table_row: {hashtag}, {price}, {date}',
        }

        self.assertEqual(
            balance.topay_render(rows,strings),
            """header: 1970-05
table_start:
table_row: Rent, 10, 1970-05-15 00:00:00
table_row: Electricity, $0, Not yet
table_row: Internet, $0, Not yet
table_row: Water, $0, Not yet
table_end:
header: 1970-06
table_start:
table_row: Rent, $0, Not yet
table_row: Electricity, $0, Not yet
table_row: Internet, $0, Not yet
table_row: Water, 10, 1970-06-17 00:00:00
table_end:
"""
        )
