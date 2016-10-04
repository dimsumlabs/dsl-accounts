
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

    def test_outgoing(self):
        object = balance.Row("100","1970-01-01","a comment","outgoing")
        self.assertEqual(object.value,-100)

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

        
