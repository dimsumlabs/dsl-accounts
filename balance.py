#!/usr/bin/env python
# Licensed under GPLv3
from collections import namedtuple
import decimal
import datetime
import argparse
import os.path
import sys
import csv
import os
import re

#
# TODO
# - make Row take Date objects and not strings with dates, removing a string
#   handling fart from Row.autosplit() and removing external formatting
#   knowledge from Row
# - Row should throw an error with negative values
# - If we know that there never negative values, we can store the Row.direction
#   content in the sign of the Row.value field
# - The "!months:[offset:]count" tag is perhaps a little awkward, find a
#   more obvious format (perhaps "!months=month[,month]+" - which is clearly
#   a more discoverable format, but would get quite verbose with yearly
#   transactions (or even just one with more than 3 months...)
#

FILES_DIR = 'cash'
IGNORE_FILES = ('membershipfees',)

# Ensure we do not invent more money
decimal.getcontext().rounding = decimal.ROUND_DOWN


class Row(namedtuple('Row', ('value', 'date', 'comment', 'direction'))):

    def __new__(cls, value, date, comment, direction):
        value = decimal.Decimal(value)
        date = datetime.datetime.strptime(date.strip(), "%Y-%m-%d").date()

        if direction not in ('incoming', 'outgoing'):
            raise ValueError('Direction "{}" unhandled'.format(direction))

        # Inverse value
        if direction == 'outgoing':
            value = decimal.Decimal(0)-value

        obj = super(cls, Row).__new__(cls, value, date, comment, direction)

        # Look at the comment for this row and extract any hashtags found
        # hashtags are used to tag the category of each transaction and
        # might be overwritten later to decorate them nicely
        obj.hashtag = obj._xtag('#')

        return obj

    def __add__(self, value):
        if isinstance(value, Row):
            value = value.value

        return self.value + value

    def __radd__(self, value):
        return self.__add__(value)

    def month(self):
        return self.date.strftime('%Y-%m')

    def _xtag(self, x):
        """Generically extract tags with a given prefix
        """
        p = re.compile(x+'([a-zA-Z]\S*)')
        all_tags = p.findall(self.comment)

        # TODO - have a better plan for what to do with multiple tags
        if len(all_tags) > 1:
            raise ValueError('Row has multiple {}tags: {}'.format(x, all_tags))

        if len(all_tags) == 0:
            return None

        return all_tags[0]

    def bangtag(self):
        """Look at the comment for this row and extract any '!' tags found
           bangtags are used to insert meta-commands (like '!months:-1:5')
        """
        return self._xtag('!')

    @staticmethod
    def _month_add(date, incr):
        """unghgnh.  I am following the pattern of not requiring any extra
           libs to be installed to use this softare.  This means that
           there are no month math functions, so I write my own

           Given a date object and a number of months to increment
           (or decrement) return a new date object
           (NOTE: no leap year processing, they are assumed not to exist)
        """
        # short cut that guarantees not to disturb the date
        if incr == 0:
            return date

        year = date.year
        month = date.month + incr
        day = date.day
        while month > 12:
            year += 1
            month -= 12
        while month < 1:
            year -= 1
            month += 12

        # clamp to maximum day of the month
        max_dom = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        day = min(day, max_dom[month-1])

        return datetime.date(year, month, day)

    def _split_dates(self):
        """extract any !months tag and use that to calculate the list of
           dates that this row could be split into
        """
        tag = self.bangtag()
        if tag is None:
            return [self.date]

        fields = tag.split(':')

        if fields[0] != 'months':       # TODO: fix this for multiple tags
            return [self.date]

        if len(fields) < 2 or len(fields) > 3:
            raise ValueError('months bang must specify one or two numbers')

        if len(fields) == 3:
            # the fields are "start:count"
            start = int(fields[1])
            end = start+int(fields[2])
        else:
            # otherwise, the field is just "count"
            start = 0
            end = int(fields[1])

        dates = []
        for i in range(start, end):
            dates.append(self._month_add(self.date, i))

        return dates

    def autosplit(self):
        """look at the split bangtag and return a split row if needed
        """
        dates = self._split_dates()

        # no splitting needed, return unchanged
        if len(dates) == 1 and dates[0] == self.date:
            return [self]

        # append a bangtag to show that something has happend to this row
        # this also means that it cannot be passed to split() twice as that
        # would find two bangtags and raise an exception
        comment = self.comment+' !child'

        # divide the value amongst all the child rows
        count_children = len(dates)
        # (The abs value is taken because the sign is in the self.direction)
        each_value = abs(self.value / count_children)
        # (avoid numbers that cannot be represented with cash by using int())
        each_value = int(each_value)

        # the remainder is any money lost due to rounding
        remainder = abs(self.value) - each_value * count_children

        rows = []
        for date in dates:
            datestr = date.strftime('%Y-%m-%d')
            this_value = each_value + remainder
            remainder = 0  # only add the remainder to the first child
            rows.append(Row(this_value, datestr, comment, self.direction))

        return rows

    def _getvalue(self, field):
        """return the field value, if the name refers to a method, call it to
           obtain the value
        """
        if not hasattr(self, field):
            raise AttributeError('Object has no attr "{}"'.format(field))
        attr = getattr(self, field)
        if callable(attr):
            attr = attr()
        return attr

    def match(self, **kwargs):
        """using kwargs, check if this Row matches if so, return it, or None
        """
        for key, value in kwargs.items():
            attr = self._getvalue(key)
            if value != attr:
                return None

        return self

    def filter(self, string):
        """Using the given human readable filter, check if this row matches
           and if so, return it, or None
        """

        # its not a real tokeniser, its just a RE. so, now I have two problems
        m = re.match("([a-z0-9_]+)([=!<>~]{1,2})(.*)", string, re.I)
        if not m:
            raise ValueError('filters must be <key><op><value>')

        field = m.group(1)
        op = m.group(2)
        value_match = m.group(3)
        value_now = str(self._getvalue(field))

        if op == '==':
            if value_now == value_match:
                return self
        elif op == '!=':
            if value_now != value_match:
                return self
        elif op == '>':
            if value_now > value_match:
                return self
        elif op == '<':
            if value_now < value_match:
                return self
        elif op == '=~':
            if re.search(value_match, value_now, re.I):
                return self
        else:
            raise ValueError('Unknown filter operation "{}"'.format(op))

        return None


def parse_dir(dirname):   # pragma: no cover
    '''Take all files in dirname and return Row instances'''

    for filename in os.listdir(dirname):
        if filename in IGNORE_FILES:
            continue

        direction, _ = filename.split('-', 1)

        with open(os.path.join(dirname, filename), 'r') as tsvfile:
            reader = csv.reader(tsvfile, delimiter='\t')

            for row in reader:
                yield Row(*row, direction=direction)


def apply_filter_strings(filter_strings, rows):
    """Apply the given list of human readable filters to the rows
    """
    if filter_strings is None:
        filter_strings = []
    for row in rows:
        match = True
        for s in filter_strings:
            if not row.filter(s):
                match = False
                break
        if match:
            yield row


def grid_accumulate(rows):
    """Accumulate the rows into month+tag buckets
    """
    months = set()
    tags = set()
    grid = {}
    totals = {}
    totals['total'] = 0

    # Accumulate the data
    for row in rows:
        month = row.month()
        tag = row.hashtag

        if tag is None:
            tag = 'unknown'

        tag = tag.capitalize()

        # I would prefer auto-vivification to all these if statements
        if tag not in grid:
            grid[tag] = {}
        if month not in grid[tag]:
            grid[tag][month] = {'sum': 0, 'last': datetime.date(1970, 1, 1)}
        if month not in totals:
            totals[month] = 0

        # sum this row into various buckets
        grid[tag][month]['sum'] += row.value
        grid[tag][month]['last'] = max(row.date, grid[tag][month]['last'])
        totals[month] += row.value
        totals['total'] += row.value
        months.add(month)
        tags.add(tag)

    return months, tags, grid, totals


def grid_render_colheader(months, months_len, tags_len):
    s = []

    # Skip the column of tag names
    s.append(' '*tags_len)

    # Output the month row headings
    for month in months:
        s.append("{:>{}}".format(month, months_len))

    s.append("\n")

    return s


def grid_render_totals(months, totals, months_len, tags_len):
    s = []

    s.append("\n")
    s.append("{:<{width}}".format('TOTALS', width=tags_len))

    for month in months:
        s.append("{:>{}}".format(totals[month], months_len))

    s.append("\n")
    s.append("{:<{width}}".format('RUNNING TOTALS', width=tags_len))

    running_total = 0
    for month in months:
        running_total += totals[month]
        s.append("{:>{}}".format(running_total, months_len))

    s.append("\n")
    s.append("TOTAL: {:>{}}".format(totals['total'], months_len))

    return s


def grid_render_rows(months, tags, grid, months_len, tags_len):
    s = []

    # Output each tag
    for tag in tags:
        row = ''
        row += "{:<{width}}".format(tag, width=tags_len)

        for month in months:
            if month in grid[tag]:
                col = grid[tag][month]['sum']
            else:
                col = ''
            row += "{:>{}}".format(col, months_len)

        row += "\n"
        s.append(row)

    return s


def grid_render_datagroom(months, tags):
    # how much room to allow for the tags
    tags_len = max([len(i) for i in tags])
    tags_len += 1

    # how much room to allow for each month column
    months_len = 9

    months = sorted(months)
    tags = sorted(tags)

    return months, tags, months_len, tags_len


def grid_render(months, tags, grid, totals):
    # Render the accumulated data

    (months, tags, months_len, tags_len) = grid_render_datagroom(months, tags)

    s = []
    s += grid_render_colheader(months, months_len, tags_len)
    s += grid_render_rows(months, tags, grid, months_len, tags_len)
    s += grid_render_totals(months, totals, months_len, tags_len)

    return ''.join(s)


def topay_render(rows, strings):
    rows = apply_filter_strings(['direction==outgoing'], rows)
    (months, tags, grid, totals) = grid_accumulate(rows)

    s = []
    for month in sorted(months):
        s.append(strings['header'].format(date=month))
        s.append("\n")
        s.append(strings['table_start'])
        s.append("\n")
        for hashtag in sorted(tags):
            if month in grid[hashtag]:
                price = grid[hashtag][month]['sum']
                date = grid[hashtag][month]['last']
            else:
                price = "$0"
                date = "Not Yet"

            s.append(strings['table_row'].format(hashtag=hashtag.capitalize(),
                                                 price=price, date=date))
            s.append("\n")
        s.append(strings['table_end'])
        s.append("\n")

    return ''.join(s)


#
# This section contains the implementation of the commandline
# sub-commands.  Ideally, they are all small and simple, implemented with
# calls to the above functions.  This will allow the simple unit tests
# to provide confidence that none of the above functions are broken,
# without needing the sub-commands to be tested (which would need a
# more complex test system)
#


def subp_sum(args):  # pragma: no cover
    print("{}".format(sum(args.rows)))


def subp_topay(args):  # pragma: no cover
    strings = {
        'header': 'Date: {date}',
        'table_start': "Bill\t\t\tPrice\tPay Date",
        'table_end': '',
        'table_row': "{hashtag:<23}\t{price}\t{date}",
    }
    print(topay_render(args.rows, strings))


def subp_topay_html(args):  # pragma: no cover
    strings = {
        'header': '<h2>Date: <i>{date}</i></h2>',
        'table_start':
            "<table>\n" +
            "<tr><th>Bills</th><th>Price</th><th>Pay Date</th></tr>",
        'table_end': '</table>',
        'table_row': '''
    <tr>
        <td>{hashtag}</td><td>{price}</td><td>{date}</td>
    </tr>''',
    }
    print(topay_render(args.rows, strings))


def subp_party(args):  # pragma: no cover
    balance = sum(args.rows)
    print("Success" if balance > 0 else "Fail")


def subp_csv(args):  # pragma: no cover
    rows = sorted(args.rows, key=lambda x: x.date)

    with args.csv_out as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow([row.capitalize() for row in Row._fields])

        for row in rows:
            writer.writerow(row)

        writer.writerow('')
        writer.writerow(('Sum',))
        writer.writerow((sum(rows),))


def subp_grid(args):  # pragma: no cover
    # ensure that each category has a nice and clear prefix
    for row in args.rows:
        if row.hashtag is None:
            row.hashtag = 'unknown'

        if row.direction == 'outgoing':
            row.hashtag = 'out ' + row.hashtag
        else:
            row.hashtag = 'in ' + row.hashtag

    (months, tags, grid, totals) = grid_accumulate(args.rows)
    print(grid_render(months, tags, grid, totals))


def subp_make_balance(args):
    def _format_tpl(tpl, key, value):
        '''Poor mans template engine'''
        return tpl.replace(('{%s}' % key), value)

    with open('./docs/template.html') as f:
        tpl = f.read()

    # Filter out only the membership dues
    grid_rows = list(apply_filter_strings([
        'direction==incoming',
        'hashtag=~^dues:',
    ], args.rows))

    # Make the category look pretty
    for row in grid_rows:
        a = row.hashtag.split(':')
        row.hashtag = ''.join(a[1:]).title()

    (months, tags, grid, totals) = grid_accumulate(grid_rows)
    (months, tags, months_len, tags_len) = grid_render_datagroom(months, tags)

    header = ''.join(grid_render_colheader(months, months_len, tags_len))
    grid = ''.join(grid_render_rows(months, tags, grid, months_len, tags_len))

    tpl = _format_tpl(tpl, 'balance_sum', str(sum(args.rows)))
    tpl = _format_tpl(tpl, 'grid_header', header)
    tpl = _format_tpl(tpl, 'grid', grid)
    # TODO: calculate when rent is due and add another field to the template

    print(tpl)


# A list of all the sub-commands
subp_cmds = {
    'sum': {
        'func': subp_sum,
        'help': 'Sum all transactions',
    },
    'make_balance': {
        'func': subp_make_balance,
        'help': 'Output sum HTML page',
    },
    'topay': {
        'func': subp_topay,
        'help': 'List all pending payments',
    },
    'topay_html': {
        'func': subp_topay_html,
        'help': 'List all pending payments as HTML table',
    },
    'party': {
        'func': subp_party,
        'help': 'Is it party time or not?',
    },
    'csv': {
        'func': subp_csv,
        'help': 'Output transactions as csv',
    },
    'grid': {
        'func': subp_grid,
        'help': 'Output a grid of transaction tags vs months',
    },
}

#
# Most of this is boilerplate and stays the same even with addition of
# features.  The only exception is if a sub-command needs to add a new
# commandline option.
#
if __name__ == '__main__':  # pragma: no cover
    argparser = argparse.ArgumentParser(
        description='Run calculations and transformations on cash data')
    argparser.add_argument('--dir',
                           action='store',
                           type=str,
                           default=FILES_DIR,
                           help='Input directory')
    argparser.add_argument('--filter', action='append',
                           help='Add a key=value filter to the rows used')
    argparser.add_argument('--split',
                           action='store_const', const=True,
                           default=False,
                           help='Split rows that cover multiple months')

    subp = argparser.add_subparsers(help='Subcommand', dest='cmd')
    subp.required = True
    for key, value in subp_cmds.items():
        value['parser'] = subp.add_parser(key, help=value['help'])
        value['parser'].set_defaults(func=value['func'])

    # Add a new commandline option for the "csv" subcommand
    subp_cmds['csv']['parser'].add_argument('--out',
                                            type=argparse.FileType('w'),
                                            default=sys.stdout,
                                            dest='csv_out',
                                            help='Output file')

    args = argparser.parse_args()

    if not os.path.exists(args.dir):
        raise RuntimeError('Directory "{}" does not exist'.format(args.dir))

    # first, load the data
    args.rows = parse_dir(args.dir)

    # optionally split multi-month transactions into one per month
    if args.split:
        tmp = []
        for orig_row in args.rows:
            tmp.extend(orig_row.autosplit())
        args.rows = tmp

    # apply any filters requested
    args.rows = list(apply_filter_strings(args.filter, args.rows))

    args.func(args)
