
""" Perform tests on the balance.py
"""

import unittest
import datetime
import sys
import json
if sys.version_info[0] == 2:  # pragma: no cover
    import mock
else:
    from unittest import mock  # pragma: no cover

import balance # noqa


class fakedatetime(datetime.datetime):

    @classmethod
    def now(cls):
        return cls(1990, 5, 4, 12, 12, 12, 0)


class TestRowSet(unittest.TestCase):
    def setUp(self):
        r = [None for x in range(6)]
        r[0] = balance.Row("10", "1970-02-06", "comment4", "outgoing")
        r[1] = balance.Row("10", "1970-01-05", "comment1", "incoming")
        r[2] = balance.Row("10", "1970-01-10", "comment2 #rent", "outgoing")
        r[3] = balance.Row("10", "1970-01-01", "comment3 #water", "outgoing")
        r[4] = balance.Row("10", "1970-03-01", "comment5 #rent", "outgoing")
        r[5] = balance.Row("15", "1970-01-11", "comment6 #water !months:3", "outgoing") # noqa
        self.rows_array = r

        self.rows = balance.RowSet()

    def tearDown(self):
        self.rows_array = None
        self.rows = None

    def test_value(self):
        self.rows.append(self.rows_array)

        self.assertEqual(self.rows.value, -45)

        self.rows.append(balance.Row("0.5", "1970-03-12", "comment9", "outgoing")) # noqa
        self.rows.append(balance.Row("0.5", "1970-03-13", "comment10", "outgoing")) # noqa
        self.assertEqual(str(self.rows.value), '-46')

    def test_nested_rowset(self):
        self.rows.append(self.rows_array)

        r = [None for x in range(2)]
        r[0] = balance.Row("13", "1971-02-06", "comment7", "outgoing")
        r[1] = balance.Row("12", "1971-01-05", "comment8", "incoming")
        self.rows.append(r)

        self.assertEqual(self.rows.value, -46)

    def test_append(self):
        self.rows.append(self.rows_array[0])

        # FIXME - looking inside the object
        self.assertEqual(len(self.rows.rows), 1)

        self.rows.append(self.rows_array)

        # FIXME - looking inside the object
        self.assertEqual(len(self.rows.rows), 7)

        # FIXME - test appending a generator

        with self.assertRaises(ValueError):
            self.rows.append(None)

    def test_filter(self):
        self.rows.append(self.rows_array)

        self.assertEqual(
            # FIXME - looking inside the object
            self.rows.filter(["comment==comment1", "month==1970-01"]).rows,
            self.rows_array[1:2]
        )

        self.assertEqual(
            # FIXME - looking inside the object
            self.rows.filter(None).rows,
            self.rows_array
        )

    def test_autosplit(self):
        self.rows.append(self.rows_array)

        # FIXME - looking inside the object
        self.assertEqual(len(self.rows.autosplit().rows), 8)

    def test_group_by(self):
        self.rows.append(self.rows_array)

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


class TestMisc(unittest.TestCase):
    def setUp(self):
        r = [None for x in range(6)]
        r[0] = balance.Row("10", "1970-02-06", "comment4", "outgoing")
        r[1] = balance.Row("10", "1970-01-05", "comment1", "incoming")
        r[2] = balance.Row("10", "1970-01-10", "comment2 #rent", "outgoing")
        r[3] = balance.Row("10", "1970-01-01", "comment3 #water", "outgoing")
        r[4] = balance.Row("10", "1970-03-01", "comment5 #rent", "outgoing")
        r[5] = balance.Row("15", "1970-01-11", "comment6 #water", "outgoing")

        self.rows = balance.RowSet()
        self.rows.append(r)

    def tearDown(self):
        self.rows = None

    def test_grid_accumulate(self):
        self.assertEqual(
            balance.grid_accumulate(self.rows), (
                set([
                    datetime.date(1970, 1, 1),
                    datetime.date(1970, 2, 1),
                    datetime.date(1970, 3, 1),
                ]),
                {
                    'water': {
                        datetime.date(1970, 1, 1): {
                            'sum': -25,
                        },
                    },
                    'unknown': {
                        datetime.date(1970, 1, 1): {
                            'sum': 10,
                        },
                        datetime.date(1970, 2, 1): {
                            'sum': -10,
                        },
                    },
                    'rent': {
                        datetime.date(1970, 3, 1): {
                            'sum': -10,
                        },
                        datetime.date(1970, 1, 1): {
                            'sum': -10,
                        },
                    },
                },
                {
                    datetime.date(1970, 1, 1): -25,
                    datetime.date(1970, 2, 1): -10,
                    datetime.date(1970, 3, 1): -10,
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

        (m, grid, total) = balance.grid_accumulate(self.rows)
        t = self.rows.group_by('hashtag')

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

        self.rows = balance.RowSet()
        self.rows.append(r)

    def tearDown(self):
        self.rows = None

    def test_sum(self):
        self.assertEqual(balance.subp_sum(self), "10")

        # FIXME - check the assertion for negative sums

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

    def test_csv(self):
        expect = [
            'Value,Date,Comment\r',
            '500,1990-04-03,#dues:test1\r',
            '20,1990-04-03,Unknown\r',
            '-12500,1990-04-15,#bills:rent\r',
            '-1500,1990-04-26,#clubmate\r',
            '1500,1990-04-27,#clubmate\r',
            '-1174,1990-04-27,#bills:electric\r',
            '500,1990-05-02,#dues:test1\r',
            '-488,1990-05-25,#bills:internet\r',
            '13152,1990-05-25,balance books\r',
            '\r',
            'Sum\r',
            '10\r',
            '',
        ]

        got = balance.subp_csv(self).split("\n")
        self.assertEqual(got, expect)

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

    def test_json_payments(self):
        expect = {
            'unknown':    '1990-05',
            'clubmate':   '1990-04',
            'dues:test1': '1990-05',
        }
        got = json.loads(balance.subp_json_payments(self))
        self.assertEqual(got, expect)

    @mock.patch('balance.datetime.datetime', fakedatetime)
    def test_make_balance(self):
        got = balance.subp_make_balance(self)

        # this is the {grid_header} and {grid} values from the template
        want = "        1990-04  1990-05\nTest1       500      500\n"
        self.assertTrue(want in got)

        # this is the {rent_due} value from the template, with some of
        # the template mixed in
        # TODO - have a testable "rowset.forcastNext(category)" function
        want = '(due on: <span class="color_neg">1990-04-23</span>) Rent:'
        self.assertTrue(want in got)

    @mock.patch('balance.datetime.datetime', fakedatetime)
    def test_stats(self):
        # FIXME - this would look more meaningful with at least one more
        #         month's data
        expect = [
            '                 1990-04    Average    MonthTD      Total',
            'outgoing          -15174     -15174       -488     -15174',
            'incoming            2020       2020      13652       2020',
            '',
            ' dues:               500        500        500        500',
            ' other:             1520       1520      13152       1520',
            '',
            'nr members             1          1          1          1',
            'ARPM                 500        500        500        500',
            '',
            'members needed',
            ' dues 500             31         31',
            ' dues 600             26         26',
            ' dues 700             22         22',
            'dues needed',
            ' members 17          892        892',
            ' members 20          758        758',
            ' members 25          606        606',
            ' members 30          505        505',
            '',
            'Note: Total column does not include MonthTD numbers',
            '',
        ]

        got = balance.subp_stats(self).split("\n")
        self.assertEqual(got, expect)
