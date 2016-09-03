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

def find_hashtag(keyword, rows):
   '''Find a hash tag in the payment history'''
   for row in rows:
      if(row.comment.__contains__('#'+keyword)):
         return True,-row.value,row.date
   return False,'$0','Not yet'

def parse_dir(dirname):
    '''Take all files in dirname and return Row instances'''

    for filename in os.listdir(dirname):
        direction, _ = filename.split('-', 1)

        with open(os.path.join(dirname, filename), 'r') as tsvfile:
            reader = csv.reader(tsvfile, delimiter='\t')

            for row in reader:
                yield Row(*row, direction=direction)

def parse_outgoing_payments(dirname,date):
    '''Take all files in dirname and return Row instances'''

    with open(os.path.join(dirname, 'outgoing-'+date), 'r') as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')

        for row in reader:
            yield Row(*row, direction='outgoing')

def get_outgoing_payment_months(dirname):
    ret_array=[]
    for filename in os.listdir(dirname):
        direction, date = filename.split('-', 1)
        if direction == "outgoing":
             ret_array.append(date)
    return ret_array

argparser = argparse.ArgumentParser(
    description='Run calculations and transformations on cash data')
argparser.add_argument('--dir',
                       action='store',
                       type=str,
                       default=FILES_DIR,
                       help='Input directory')
subp = argparser.add_subparsers(help='Subcommand', dest='cmd')
subp.required = True
subp.add_parser('topay', help='List all pending payments')
subp.add_parser('topay_html', help='List all pending payments as HTML table')
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

    elif args.cmd == 'topay':
        for date in get_outgoing_payment_months(args.dir):
            print('Date: '+date)
            print('Bill       \tPrice\tPay Date')
            rows = sorted(parse_outgoing_payments(args.dir,date), key=lambda x: x.date)
            paid,price,date = find_hashtag('rent',rows)
            print('Rent       \t'+str(price)+'\t'+str(date))
            paid,price,date = find_hashtag('electricity',rows)
            print('Electricity\t'+str(price)+'\t'+str(date))
            paid,price,date = find_hashtag('internet',rows)
            print('Internet   \t'+str(price)+'\t'+str(date))
            paid,price,date = find_hashtag('water',rows)
            print('Water      \t'+str(price)+'\t'+str(date))

    elif args.cmd == 'topay_html':
        for date in get_outgoing_payment_months(args.dir):
            print('<h2>Date: <i>'+date+'</i></h2>')
            rows = sorted(parse_outgoing_payments(args.dir,date), key=lambda x: x.date)
            print('<table>')
            print('<tr><th>Bills</th><th>Price</th><th>Pay Date</th></tr>')
	    paid,price,date = find_hashtag('rent',rows)
            print('<tr><td>Rent</td><td>'+str(price)+'</td><td>'+str(date)+'</td></tr>')
	    paid,price,date = find_hashtag('electricity',rows)
            print('<tr><td>Electric</td><td>'+str(price)+'</td><td>'+str(date)+'</td></tr>')
            paid,price,date = find_hashtag('internet',rows)
            print('<tr><td>Internet</td><td>'+str(price)+'</td><td>'+str(date)+'</td></tr>')
            paid,price,date = find_hashtag('water',rows)
            print('<tr><td>Water</td><td>'+str(price)+'</td><td>'+str(date)+'</td></tr>')
            print('</table>')

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
