#!/usr/bin/env python
# Licensed under GPLv3
from collections import namedtuple
from decimal import Decimal
import datetime
import argparse
import os.path
import sys
import csv
import os
import re


FILES_DIR = 'cash'
IGNORE_FILES = ('membershipfees',)


class Row(namedtuple('Row', ('value', 'date', 'comment', 'direction'))):

    def __new__(cls, value, date, comment, direction):
        value = Decimal(value)
        date = datetime.datetime.strptime(date.strip(), "%Y-%m-%d").date()

        if direction not in ('incoming', 'outgoing'):
            raise ValueError('Direction "{}" unhandled'.format(direction))

        # Inverse value
        if direction == 'outgoing':
            value = Decimal(0)-value

        obj = super(cls, Row).__new__(cls, value, date, comment, direction)
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
        p = re.compile(x+'(\S+)')
        all_tags = p.findall(self.comment)

        # TODO - have a better plan for what to do with multiple tags
        if len(all_tags) > 1:
            raise ValueError('Row has multiple {}tags: {}'.format(x, all_tags))

        if len(all_tags) == 0:
            return None

        return all_tags[0]

    def hashtag(self):
        """Look at the comment for this row and extract any hashtags found
           hashtags are used to tag the category of each transaction
        """
        return self._xtag('#')

    def bangtag(self):
        """Look at the comment for this row and extract any '!' tags found
           bangtags are used to insert meta-commands (like '!months:-1:5')
        """
        return self._xtag('!')

    def _month_add(ignore, date, incr):
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

        if int(fields[1]) < 0:
            # a negative number indicates the fields are "start:count"
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

    def match(self, **kwargs):
        """using kwargs, check if this Row matches if so, return it, or None
        """

        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError('Object has no attr "{}"'.format(key))
            attr = getattr(self, key)
            if callable(attr):
                attr = attr()
            if value != attr:
                return None

        return self


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
    filters = {}
    if filter_strings:
        for s in filter_strings:
            try:
                (key, value) = s.split('=')
            except ValueError:
                raise ValueError('Filters must be "key=value", '
                                 '"{}" is not'.format(s))
            filters[key] = value

    for row in rows:
        if row.match(**filters):
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
        tag = row.hashtag()

        if tag is None:
            tag = 'unknown'

        if row.direction == 'outgoing':
            tag = 'out ' + tag
        else:
            tag = 'in ' + tag

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

    return (months, tags, grid, totals)


def grid_render(months, tags, grid, totals):
    # Render the accumulated data
    s = []

    tags_len = max([len(i) for i in tags])
    months = sorted(months)

    # Skip the column of tag names
    s.append(' '*tags_len)
    s.append("\t")

    # Output the month row headings
    for month in months:
        s.append(month)
        s.append("\t")

    s.append("\n")

    # Output each tag
    for tag in sorted(tags):
        s.append("{:<{width}}\t".format(tag, width=tags_len))

        for month in months:
            if month in grid[tag]:
                s.append("{:>7}\t".format(grid[tag][month]['sum']))
            else:
                s.append("\t")

        s.append("\n")

    s.append("\n")
    s.append("{:<{width}}\t".format('TOTALS', width=tags_len))

    for month in months:
        s.append("{:>7}\t".format(totals[month]))

    s.append("\n")
    s.append("TOTAL:\t{:>7}".format(totals['total']))

    return ''.join(s)


def topay_render(rows, strings):
    rows = apply_filter_strings(['direction=outgoing'], rows)
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
    (months, tags, grid, totals) = grid_accumulate(args.rows)
    print(grid_render(months, tags, grid, totals))


# A list of all the sub-commands
subp_cmds = {
    'sum': {
        'func': subp_sum,
        'help': 'Sum all transactions',
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

    args.rows = apply_filter_strings(args.filter, parse_dir(args.dir))

    args.func(args)
