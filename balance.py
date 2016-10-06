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


FILES_DIR = 'cash'
IGNORE_FILES = ('membershipfees',)
HASHTAGS = ('rent', 'electricity', 'internet', 'water')


def list_files(dirname):
    for f in os.listdir(dirname):
        if f not in IGNORE_FILES:
            yield f


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


def find_hashtag(keyword, rows):
    '''Find a hash tag in the payment history'''
    for row in rows:
        if '#{}'.format(keyword) in row.comment:
            return (True, -row.value, row.date)
    return (False, '$0', 'Not yet')


def parse_dir(dirname):
    '''Take all files in dirname and return Row instances'''

    for filename in list_files(dirname):
        direction, _ = filename.split('-', 1)

        with open(os.path.join(dirname, filename), 'r') as tsvfile:
            reader = csv.reader(tsvfile, delimiter='\t')

            for row in reader:
                yield Row(*row, direction=direction)


def filter_outgoing_payments(rows, month):
    '''Filter the given rows list for outgoing payments in the given month'''
    ret = []

    for row in rows:
        if row.month() == month and row.direction == 'outgoing':
            ret.append(row)

    ret.sort(key=lambda x: x.date)
    return ret


def get_outgoing_payment_months(dirname):
    ret_array = []
    for filename in list_files(dirname):
        direction, date = filename.split('-', 1)
        if direction == "outgoing":
            ret_array.append(date)
    return ret_array

def topay_render(dir,strings):
    # yes, this is not ideal, since we load in all the 'incoming' transactions
    # but just how much transaction data are we expecting, anyway?
    all_rows = list(parse_dir(dir))

    for date in get_outgoing_payment_months(dir):
        print(strings['header'].format(date=date))
        rows = filter_outgoing_payments(all_rows, date)
        print(strings['table_start'])
        for hashtag in HASHTAGS:
            paid, price, date = find_hashtag(hashtag, rows)
            print(strings['table_row'].format(hashtag=hashtag.capitalize(),
                                       price=price, date=date))
        print(strings['table_end'])


def subp_sum(args):
    print("{}".format(sum(parse_dir(args.dir))))

def subp_topay(args):
    strings = {
        'header': 'Date: {date}',
        'table_start': "Bill\t\tPrice\tPay Date",
        'table_end': '',
        'table_row': "{hashtag:<15}\t{price}\t{date}",
    }
    topay_render(args.dir,strings)

def subp_topay_html(args):
    strings = {
        'header': '<h2>Date: <i>{date}</i></h2>',
        'table_start':
            "<table>\n"+
            "<tr><th>Bills</th><th>Price</th><th>Pay Date</th></tr>",
        'table_end': '</table>',
        'table_row': '''
    <tr>
        <td>{hashtag}</td><td>{price}</td><td>{date}</td>
    </tr>''',
    }
    topay_render(args.dir,strings)

def subp_party(args):
    balance = sum(parse_dir(args.dir))
    print("Success" if balance > 0 else "Fail")

def subp_csv(args):
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
    }
}

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(
        description='Run calculations and transformations on cash data')
    argparser.add_argument('--dir',
                           action='store',
                           type=str,
                           default=FILES_DIR,
                           help='Input directory')
    subp = argparser.add_subparsers(help='Subcommand', dest='cmd')
    subp.required = True
    for key,value in subp_cmds.iteritems():
        value['parser'] = subp.add_parser(key, help=value['help'])

    subp_cmds['csv']['parser'].add_argument('--out',
                            action='store',
                            type=str,
                            default=None,
                            dest='csv_out',
                            help='Output file')

    args = argparser.parse_args()

    if not os.path.exists(args.dir):
        raise RuntimeError('Directory "{}" does not exist'.format(args.dir))

    if args.cmd in subp_cmds:
        subp_cmds[args.cmd]['func'](args)

    else:
        raise ValueError('Unknown command "{}"'.format(args.cmd))
