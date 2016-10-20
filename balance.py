#!/usr/bin/env python
# Licensed under GPLv3
from collections import namedtuple
from datetime import datetime
from decimal import Decimal
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
        date = datetime.strptime(date.strip(), "%Y-%m-%d")

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

    def hashtag(self):
        """Look at the comment for this row and extract any hashtags found
        """
        p = re.compile('#(\S+)')
        all_tags = p.findall(self.comment)

        # TODO - have a better plan for what to do with multiple tags
        if len(all_tags) > 1:
            raise ValueError('Row has multiple tags: {}'.format(all_tags))

        if len(all_tags) == 0:
            return None

        return all_tags[0]

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


def grid_accumulate(rows):
    """Accumulate the rows into month+tag buckets, then render this as text
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
            grid[tag][month] = {'sum': 0, 'last': datetime(1970, 1, 1, 0, 0)}
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


def topay_render(all_rows, strings):
    rows = [row for row in all_rows if row.match(direction='outgoing')]
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
    print("{}".format(sum(parse_dir(args.dir))))


def subp_topay(args):  # pragma: no cover
    strings = {
        'header': 'Date: {date}',
        'table_start': "Bill\t\t\tPrice\tPay Date",
        'table_end': '',
        'table_row': "{hashtag:<23}\t{price}\t{date}",
    }
    all_rows = list(parse_dir(args.dir))
    print(topay_render(all_rows, strings))


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
    all_rows = list(parse_dir(args.dir))
    print(topay_render(all_rows, strings))


def subp_party(args):  # pragma: no cover
    balance = sum(parse_dir(args.dir))
    print("Success" if balance > 0 else "Fail")


def subp_csv(args):  # pragma: no cover
    rows = sorted(parse_dir(args.dir), key=lambda x: x.date)

    with (open(args.csv_out, 'w') if args.csv_out else sys.stdout) as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow([row.capitalize() for row in Row._fields])

        for row in rows:
            writer.writerow(row)

        writer.writerow('')
        writer.writerow(('Sum',))
        writer.writerow((sum(rows),))


def subp_grid(args):  # pragma: no cover
    rows = list(parse_dir(args.dir))
    (months, tags, grid, totals) = grid_accumulate(rows)
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
    subp = argparser.add_subparsers(help='Subcommand', dest='cmd')
    subp.required = True
    for key, value in subp_cmds.items():
        value['parser'] = subp.add_parser(key, help=value['help'])
        value['parser'].set_defaults(func=value['func'])

    # Add a new commandline option for the "csv" subcommand
    subp_cmds['csv']['parser'].add_argument('--out',
                                            action='store',
                                            type=str,
                                            default=None,
                                            dest='csv_out',
                                            help='Output file')

    args = argparser.parse_args()

    if not os.path.exists(args.dir):
        raise RuntimeError('Directory "{}" does not exist'.format(args.dir))

    args.func(args)
