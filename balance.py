#!/usr/bin/env python3
# Licensed under GPLv3
from collections import namedtuple
from datetime import datetime
from decimal import Decimal
import argparse
import os.path
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

if __name__ == '__main__':
    args = argparser.parse_args()

    if not os.path.exists(args.dir):
        raise RuntimeError('Directory "{}" does not exist'.format(args.dir))

    if args.cmd == 'sum':
        print("Sum:\t{}".format(sum(parse_dir(args.dir))))

    else:
        raise ValueError('Unknown command "{}"'.format(args.cmd))
