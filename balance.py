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


class Row(namedtuple('Row', ('value', 'date', 'comment'))):

    def __new__(cls, value, date, comment, direction):
        value = Decimal(value)
        date = datetime.strptime(date, "%Y-%m-%d")

        if direction not in ('incoming', 'outgoing'):
            raise ValueError('Direction "{}" unhandled'.format(direction))

        # Inverse value
        if direction == 'outgoing':
            value = Decimal(0)-value

        obj = super(cls, Row).__new__(cls, value, date, comment)
        return obj

    def __add__(self, value):
        if isinstance(value, Row):
            value = value.value

        return self.value + value

    def __radd__(self, value):
        return self.__add__(value)


def parse_dir(dirname):
    '''Take all files in dirname and return Row instances'''

    for filename in os.listdir(dirname):
        direction, _ = filename.split('-', 1)

        with open(os.path.join(dirname, filename), 'r') as tsvfile:
            reader = csv.reader(tsvfile, delimiter='\t')

            for row in reader:
                yield Row(*row, direction=direction)


argparser = argparse.ArgumentParser(
    description='Run calculations and transformations on cash data')
argparser.add_argument('--dir',
                       action='store',
                       type=str,
                       default=FILES_DIR,
                       help='Input directory')
subp = argparser.add_subparsers(help='Subcommand', dest='cmd')
subp.required = True
subp.add_parser('sum', help='Sum all transactions')
subp.add_parser('party', help='Is it party time or not?')
csv_parser = subp.add_parser('csv', help='Output transactions as csv')
csv_parser.add_argument('--out',
                        action='store',
                        type=str,
                        default=None,
                        dest='csv_out',
                        help='Output file')


if __name__ == '__main__':
    args = argparser.parse_args()

    if not os.path.exists(args.dir):
        raise RuntimeError('Directory "{}" does not exist'.format(args.dir))

    if args.cmd == 'sum':
        print("{}".format(sum(parse_dir(args.dir))))

    elif args.cmd == 'party':
        balance = sum(parse_dir(args.dir))
        print("Success" if balance > 0 else "Fail")

    elif args.cmd == 'csv':
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

    else:
        raise ValueError('Unknown command "{}"'.format(args.cmd))
