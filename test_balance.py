
""" Perform tests on the balance.py
"""

import unittest
import datetime
import sys
if sys.version_info[0] == 2:  # pragma: no cover
    import mock
else:
    from unittest import mock  # pragma: no cover

import balance # noqa


class fakedatetime(datetime.datetime):

    @classmethod
    def utcnow(cls):
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
        self.assertEqual(obj.filter('comment=~^foo'), None)

    @mock.patch('balance.datetime.datetime', fakedatetime)
    def test_filter_rel_months(self):
        obj = self.rows[2]
        self.assertEqual(obj.filter('rel_months<-264'), obj)
        self.assertEqual(obj.filter('rel_months<-265'), None)


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
                    ["comment==comment1", "month==1970-01"],
                    self.rows)),
            self.rows[1:2]
        )

        self.assertEqual(
            list(balance.apply_filter_strings(None, self.rows)),
            self.rows
        )

    def test_grid_accumulate(self):
        self.assertEqual(
            balance.grid_accumulate(self.rows), (
                set(['1970-03', '1970-02', '1970-01']),
                set(['Water', 'Unknown', 'Rent']),
                {
                    'Water': {
                        '1970-01': {
                            'sum': -25,
                            'last': datetime.date(1970, 1, 11)
                        },
                    },
                    'Unknown': {
                        '1970-01': {
                            'sum': 10,
                            'last': datetime.date(1970, 1, 5)
                        },
                        '1970-02': {
                            'sum': -10,
                            'last': datetime.date(1970, 2, 6)
                        },
                    },
                    'Rent': {
                        '1970-03': {
                            'sum': -10,
                            'last': datetime.date(1970, 3, 1)
                        },
                        '1970-01': {
                            'sum': -10,
                            'last': datetime.date(1970, 1, 10)
                        },
                    },
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

        expect = [
            "header: 1970-01",
            "table_start:",
            "table_row: Rent, -10, 1970-01-10",
            "table_row: Unknown, $0, Not Yet",
            "table_row: Water, -25, 1970-01-11",
            "table_end:",
            "header: 1970-02",
            "table_start:",
            "table_row: Rent, $0, Not Yet",
            "table_row: Unknown, -10, 1970-02-06",
            "table_row: Water, $0, Not Yet",
            "table_end:",
            "header: 1970-03",
            "table_start:",
            "table_row: Rent, -10, 1970-03-01",
            "table_row: Unknown, $0, Not Yet",
            "table_row: Water, $0, Not Yet",
            "table_end:",
            "",
        ]

        got = balance.topay_render(self.rows, strings).split("\n")
        self.assertEqual(got, expect)

    def test_grid_render(self):
        expect = [
            "          1970-01  1970-02  1970-03",
            "Rent          -10               -10",
            "Unknown        10      -10         ",
            "Water         -25                  ",
            "",
            "MONTH Sub Total      -25      -10      -10",
            "RUNNING Balance      -25      -35      -45",
            "TOTAL:       -45",
        ]

        (m, t, grid, total) = balance.grid_accumulate(self.rows)
        got = balance.grid_render(m, t, grid, total).split("\n")
        self.assertEqual(got, expect)


class TestSubp(unittest.TestCase):
    def setUp(self):
        r = [None for x in range(9)]
        # hey pyflakes, these look much nicer all aligned like this, but you
        # hate it, so I need to stick excludes on these lines, which just makes
        # the lines exceed 80 columns, which makes them look shit.  I choose
        # the path that messes with pyflakes the most in this case.
        r[0] = balance.Row(  "500", "1990-04-03", "#dues:test1", "incoming") # noqa
        r[1] = balance.Row(   "20", "1990-04-03", "Unknown", "incoming") # noqa
        r[2] = balance.Row( "1500", "1990-04-27", "#clubmate", "incoming") # noqa
        r[3] = balance.Row("12500", "1990-04-15", "#bills:rent", "outgoing") # noqa
        r[4] = balance.Row( "1174", "1990-04-27", "#bills:electric", "outgoing") # noqa
        r[5] = balance.Row( "1500", "1990-04-26", "#clubmate", "outgoing") # noqa
        r[6] = balance.Row(  "500", "1990-05-02", "#dues:test1", "incoming") # noqa
        r[7] = balance.Row(  "488", "1990-05-25", "#bills:internet", "outgoing") # noqa
        r[8] = balance.Row("13152", "1990-05-25", "balance books", "incoming") # noqa

        self.rows = r

    def tearDown(self):
        self.rows = None

    def test_sum(self):
        self.assertEqual(balance.subp_sum(self), "10")

    def test_topay(self):
        expect = [
            "Date: 1990-04",
            "Bill			Price	Pay Date",
            "Bills:electric         	-1174	1990-04-27",
            "Bills:internet         	$0	Not Yet",
            "Bills:rent             	-12500	1990-04-15",
            "Clubmate               	-1500	1990-04-26",
            "",
            "Date: 1990-05",
            "Bill			Price	Pay Date",
            "Bills:electric         	$0	Not Yet",
            "Bills:internet         	-488	1990-05-25",
            "Bills:rent             	$0	Not Yet",
            "Clubmate               	$0	Not Yet",
            "",
            "",
        ]
        got = balance.subp_topay(self).split("\n")
        self.assertEqual(got, expect)

    def test_topay_html(self):
        expect = [
            "<h2>Date: <i>1990-04</i></h2>",
            "<table>",
            "<tr><th>Bills</th><th>Price</th><th>Pay Date</th></tr>",
            "",
            "    <tr>",
            "        "
            "<td>Bills:electric</td><td>-1174</td><td>1990-04-27</td>",
            "    </tr>",
            "",
            "    <tr>",
            "        <td>Bills:internet</td><td>$0</td><td>Not Yet</td>",
            "    </tr>",
            "",
            "    <tr>",
            "        <td>Bills:rent</td><td>-12500</td><td>1990-04-15</td>",
            "    </tr>",
            "",
            "    <tr>",
            "        <td>Clubmate</td><td>-1500</td><td>1990-04-26</td>",
            "    </tr>",
            "</table>",
            "<h2>Date: <i>1990-05</i></h2>",
            "<table>",
            "<tr><th>Bills</th><th>Price</th><th>Pay Date</th></tr>",
            "",
            "    <tr>",
            "        <td>Bills:electric</td><td>$0</td><td>Not Yet</td>",
            "    </tr>",
            "",
            "    <tr>",
            "        "
            "<td>Bills:internet</td><td>-488</td><td>1990-05-25</td>",
            "    </tr>",
            "",
            "    <tr>",
            "        <td>Bills:rent</td><td>$0</td><td>Not Yet</td>",
            "    </tr>",
            "",
            "    <tr>",
            "        <td>Clubmate</td><td>$0</td><td>Not Yet</td>",
            "    </tr>",
            "</table>",
            "",
        ]
        got = balance.subp_topay_html(self).split("\n")
        self.assertEqual(got, expect)

    def test_party(self):
        self.assertEqual(balance.subp_party(self), "Success")
        # FIXME - add a "Fail" case too

    # FIXME - subp_csv

    def test_grid(self):
        expect = [
            "                     1990-04  1990-05",
            "In clubmate             1500         ",
            "In dues:test1            500      500",
            "In unknown                20    13152",
            "Out bills:electric     -1174         ",
            "Out bills:internet               -488",
            "Out bills:rent        -12500         ",
            "Out clubmate           -1500         ",
            "",
            "MONTH Sub Total       -13154    13164",
            "RUNNING Balance       -13154       10",
            "TOTAL:        10",
        ]

        got = balance.subp_grid(self).split("\n")
        self.assertEqual(got, expect)

# TODO - re-import the json from a string and do a deep compare
#     def test_json_dues(self):
#         r = ""
#         r += '{"test1":'
#         r += ' {"1990-05": {"sum": 500.0, "last": "1990-05-02"},'
#         r += ' "1990-04": {"sum": 500.0, "last": "1990-04-03"}}}'
#         self.assertEqual(balance.subp_json_dues(self), r)

    @mock.patch('balance.datetime.datetime', fakedatetime)
    def test_make_balance(self):
        got = balance.subp_make_balance(self)

        # this is the {grid_header} and {grid} values from the template
        want = "        1990-04  1990-05\nTest1       500      500\n\n"
        self.assertTrue(want in got)

        # this is the {rent_due} value from the template, with some of
        # the template mixed in
        # TODO - have a testable "rowset.forcastNext(category)" function
        want = 'Rent (next due: <span style="color:red">MAY 1990</span>)'
        self.assertTrue(want in got)
