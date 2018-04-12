#!/usr/bin/env python
# Licensed under GPLv3
import datetime
import argparse
import calendar
import os.path
import decimal
import string
import json
import sys
import csv
import os
import re

try:
    # python 2
    from StringIO import StringIO
except ImportError:
    # python 3
    from io import StringIO

# Ensure that we look for any modules in our local lib dir.  This allows simple
# testing and development use.  It also does not break the case where the lib
# has been installed properly on the normal sys.path
sys.path.insert(0,
                os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'lib'))
# I would use site.addsitedir, but it does an append, not insert

# Stupid pyflake, neither of these imports can be before the sys.path
from row import Row # noqa
from rowset import RowSet # noqa

# TODO
# - Implement a running balance check - perhaps using pragma lines in
#   the input - then we can add a check that the calculated balance matches
#   the known counted balance at that point in time (quick, accounting people,
#   tell me the name for this concept!).  Complicating this is the fact that
#   the running balance is split accross two files - so, this might need
#   consolidate the incoming and outgoing files.


FILES_DIR = 'cash'

# Ensure we do not invent more money
decimal.getcontext().rounding = decimal.ROUND_DOWN


def parse_dir(dirname):   # pragma: no cover
    '''Take all files in dirname and return Row instances'''

    for filename in os.listdir(dirname):
        if not re.match(r'^(incoming|outgoing)-\d{4}-\d{2}', filename):
            sys.stderr.write(
                'Filename "{}" not valid, put into proper accounting file\n'
                .format(filename))
            continue

        direction, _ = filename.split('-', 1)

        with open(os.path.join(dirname, filename), 'r') as tsvfile:
            for row in tsvfile.readlines():
                row = row.rstrip('\n')
                if not row:
                    continue
                if re.match(r'^#', row):
                    # skip comment lines
                    # - in future there might be meta/pragmas
                    continue
                yield Row(*re.split(r'\s+', row, maxsplit=2))


def render_month(date):
    """Return a short string representation of the date as a month
    """
    if isinstance(date, datetime.date):
        return date.strftime('%Y-%m')

    # Awkwardly, if we want to have a "Total" month or a "Average"
    # month, everything works except for this render_month function
    # TODO - fix this in a cleaner way
    return date


def render_month_len():
    """how much room to allow for each month column
    """
    # TODO - this should eventually move into some rendering code
    return 9


def grid_accumulate(rows):
    """Accumulate the rows into month+tag buckets
    """
    grid = {}
    totals = {}
    months_present = set()

    months = rows.group_by('month')
    for month in months:
        months_present.add(month)
        totals[month] = months[month].value

        tags = months[month].group_by('hashtag')

        for tag in tags:
            # I would prefer auto-vivification to all these if statements
            if tag not in grid:
                grid[tag] = {}

            grid[tag][month] = {}
            grid[tag][month]['sum'] = tags[tag].value

    totals['total'] = rows.value
    return months_present, grid, totals


def grid_render_onerow(prefix, prefix_len, rowdata, cell_len):
    s = []

    s += "{:<{width}}".format(prefix, width=prefix_len)

    for cell in rowdata:
        s += "{:>{}}".format(cell, cell_len)

    s += "\n"

    return s


def grid_render_colheader(months, months_len, tags_len):
    return grid_render_onerow(
        ' ', tags_len,
        [render_month(x) for x in months], months_len
    )


def grid_render_totals(months, totals, months_len, tags_len):
    s = []

    s += "\n"
    s += grid_render_onerow(
        'MONTH Sub Total', tags_len,
        [totals[x] for x in months], months_len
    )

    running_totals = []
    running_total = 0
    for month in months:
        running_total += totals[month]
        running_totals.append(running_total)

    s += grid_render_onerow(
        'RUNNING Balance', tags_len,
        running_totals, months_len
    )

    s += "TOTAL: {:>{}}".format(totals['total'], months_len)

    return s


def grid_render_rows(months, tags, grid, months_len, tags_len):
    s = []

    tags = sorted(tags)

    # Output each tag on its own row
    for tag in tags:
        cells = []
        for month in months:
            if month in grid[tag]:
                cells.append(grid[tag][month]['sum'])
            else:
                cells.append('')

        s += grid_render_onerow(
            tag, tags_len,
            cells, months_len
        )

    return s


def grid_render(months, tags, grid, totals):
    # Render the accumulated data

    tags_len = max([len(i) for i in tags])+1
    months_len = render_month_len()
    months = sorted(months)

    s = []
    s += grid_render_colheader(months, months_len, tags_len)
    s += grid_render_rows(months, tags, grid, months_len, tags_len)
    s += grid_render_totals(months, totals, months_len, tags_len)

    return ''.join(s)


def topay_render(rows, strings):
    rows = rows.filter(['direction==outgoing'])
    alltags = sorted(rows.group_by('hashtag').keys())

    months = rows.group_by('month')

    s = []
    for month in sorted(months):
        s.append(strings['header'].format(date=render_month(month)))
        s.append("\n")
        s.append(strings['table_start'])
        s.append("\n")

        monthtags = months[month].group_by('hashtag')
        for hashtag in alltags:
            if hashtag in monthtags:
                price = monthtags[hashtag].value
                date = monthtags[hashtag].last().date
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
# calls to the above functions.  This should allow clearer understanding
# of the intent of each sub-command
#


def subp_sum(args):
    result = args.rows.value
    # Only check the result for validity here and not in the class as
    # the RowSet could be storing a virtual account in other places
    if result < 0:
        raise ValueError(
            "Impossible negative value cash balance: {}".format(result))
    return "{}".format(result)


def subp_topay(args):
    strings = {
        'header': 'Date: {date}',
        'table_start': "Bill\t\t\tPrice\tPay Date",
        'table_end': '',
        'table_row': "{hashtag:<23}\t{price}\t{date}",
    }
    return topay_render(args.rows, strings)


def subp_topay_html(args):
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
    return topay_render(args.rows, strings)


def subp_party(args):
    balance = args.rows.value
    return "Success" if balance > 0 else "Fail"


def subp_csv(args):
    rows = RowSet()
    rows.append(sorted(args.rows, key=lambda x: x.date))

    buf = StringIO()
    writer = csv.writer(buf)

    # Write header
    writer.writerow([row.capitalize() for row in Row._fields])

    writer.writerows(rows)

    writer.writerow('')
    writer.writerow(('Sum',))
    writer.writerow((rows.value,))
    return buf.getvalue()


def subp_grid(args):
    # ensure that each category has a nice and clear prefix
    for row in args.rows:
        if row.hashtag is None:
            row.hashtag = 'unknown'

        if row.direction == 'outgoing':
            row.hashtag = row.hashtag + ' out'
        else:
            row.hashtag = row.hashtag + ' in'

    (months, grid, totals) = grid_accumulate(args.rows)
    tags = args.rows.group_by('hashtag').keys()

    return grid_render(months, tags, grid, totals)


def subp_json_payments(args):

    payments = args.rows.filter(['direction==incoming']).group_by('hashtag')

    r = {}
    for tag, payment in payments.items():
        r[tag] = render_month(payment.last().date)
    return json.dumps((r))


def subp_make_balance(args):
    # Load the template file
    # TODO - use a string or an arg for the template source
    with open(os.path.join(os.path.dirname(__file__),
                           './docs/template.html')) as f:
        tpl = f.read()

    # Filter out only the membership dues
    grid_rows = args.rows.filter([
        'direction==incoming',
        'hashtag=~^dues:',
        'rel_months>-5',
        'rel_months<5',
    ])

    # Make the category look pretty
    for row in grid_rows:
        a = row.hashtag.split(':')
        row.hashtag = ''.join(a[1:]).title()

    (months, grid, totals) = grid_accumulate(grid_rows)
    tags = grid_rows.group_by('hashtag').keys()
    months = sorted(months)

    months_len = render_month_len()
    tags_len = max([len(i) for i in tags])+1

    header = ''.join(grid_render_colheader(months, months_len, tags_len))
    grid = ''.join(grid_render_rows(months, tags, grid, months_len, tags_len))

    def _get_next_rent_month():
        last_payment = args.rows.group_by('hashtag')['bills:rent'].last()
        date = last_payment.date

        # The landlord states that "the monthly rental payment should
        # be settled seven (7) days in advance prior to the 1st day of
        # each and every rental month"
        #
        # Implement business logic to find this date
        #
        # assuming the rent transactions have been placed into the
        # month that they are paying the rent for, we can find the date
        # that the rent is next due by clamping the day to seven days
        # before the end of the month

        # set to the due date during at the end of the month
        date = date.replace(
            day=calendar.monthrange(date.year, date.month)[1] - 7
        )

        return date

    def _iso8601_str():
        """Why oh why is this so hard to do?
        """
        # now = datetime.datetime.now()
        # now_timestamp = now.timestamp()
        # utc_horror = datetime.datetime.utcfromtimestamp( now_timestamp ).timestamp() # noqa
        # delta_min = (now_timestamp - utc_horror) //60
        # sign="+"
        # if (delta_min<0):
        #     sign="-"
        #     delta_min = abs(delta_min)

        # delta_hr = delta_min /60.0
        # delta_min = (int(delta_hr) - delta_hr) * 60
        # delta_hr = int(delta_hr)
        # delta_str = sign+"{:02d}:{:02d}".format(delta_hr, delta_min)

        now = datetime.datetime.utcnow()
        delta_str = "Z"
        return now.strftime('%FT%T') + delta_str

    macros = {
        'balance_sum': args.rows.value,
        'grid_header': header,
        'grid':        grid,
        'rent_due':    _get_next_rent_month(),
        'time_now':    _iso8601_str(),
    }
    return string.Template(tpl).substitute(macros)


def subp_stats(args):
    # stats are only likely to be valid for previous months
    rows = args.rows.filter(['rel_months<0'])
    current_month = args.rows.filter(['rel_months==0'])

    def make_rowset(value):
        r = RowSet()
        r.append(Row(value, '1970-01-01', 'fake row'))
        return r

    def stats_rowset(rowset):
        r = {}
        r['incoming'] = rowset.filter(['value>0'])
        r['outgoing'] = rowset.filter(['value<0'])
        # TODO - values of zero?  we have one member as such, but it is a
        # exceptional case
        r['dues']     = rowset.filter(['hashtag=~^dues:']) # noqa
        r['members']  = len(r['dues'].group_by('hashtag').keys()) # noqa
        if r['members']:
            r['ARPM'] = int(r['dues'].value / r['members']) # noqa
        else:
            r['ARPM'] = -1

        r['other']    = rowset.filter(['value>0','hashtag!~^dues:']) # noqa

        return r

    result = {}
    months = rows.group_by('month')
    for k, month in months.items():
        result[k] = stats_rowset(month)

    months_len = render_month_len()+2
    tags_len = 13

    months = sorted(result.keys())

    result['Total'] = stats_rowset(rows)

    result['Average'] = {}
    for tag in ('outgoing', 'incoming', 'dues', 'other'):
        result['Average'][tag] = make_rowset(
            result['Total'][tag].value / len(months))
    result['Average']['members'] = int(sum(
        [result[x]['members'] for x in months]
    ) / len(months))
    result['Average']['ARPM'] = int(
        result['Total']['dues'].value /
        result['Average']['members'] /
        len(months)
    )

    result['MonthTD'] = stats_rowset(current_month)

    months.append('Average')
    months.append('MonthTD')
    months.append('Total')

    s = []
    s += grid_render_colheader(months, months_len, tags_len)
    for tag in ('outgoing', 'incoming'):
        s += grid_render_onerow(
            tag, tags_len,
            [result[x][tag].value.to_integral_exact(
                    rounding=decimal.ROUND_FLOOR
                ) for x in months],
            months_len
        )
    s += "\n"
    for tag in ('dues', 'other'):
        s += grid_render_onerow(
            " {}:".format(tag), tags_len,
            [result[x][tag].value.to_integral_exact(
                    rounding=decimal.ROUND_FLOOR
                ) for x in months],
            months_len
        )
    s += "\n"
    s += grid_render_onerow(
        'nr members', tags_len,
        [result[x]['members'] for x in months],
        months_len
    )
    s += grid_render_onerow(
        'ARPM', tags_len,
        [result[x]['ARPM'] for x in months],
        months_len
    )

    # The rows after this are identical in the Average and Total columns,
    # so to make that easier to see, remove the Total column from display
    # Also remove the MonthTD, since the calcualted numbers will be bogus
    # until near the end of the month
    months = months[:-2]

    def members_given_dues_outgoing(dues, rowset):
        months = len(rowset.group_by('month').keys())
        total_dues = dues * months
        return abs((rowset.value / total_dues).to_integral_exact(
                rounding=decimal.ROUND_FLOOR
        ))

    def dues_given_members_outgoing(members, rowset):
        if members == 0:
            # no value possible!
            return 0

        months = len(rowset.group_by('month').keys())
        return abs(rowset.value / members / months).to_integral_exact(
                rounding=decimal.ROUND_FLOOR
        )

    s += "\n"
    s += "members needed\n"

    # Which fee rates do we want to see membership numbers for?
    # Add in the recent official numbers
    fees_rates = set([500, 700])
    # Also add in some of the average revenue numbers
    fees_rates.add(result['Average']['ARPM'])
    fees_rates.add(result['MonthTD']['ARPM'])
    for dues in sorted(fees_rates):
        s += grid_render_onerow(
            " dues {}".format(dues), tags_len,
            [members_given_dues_outgoing(dues, result[x]['outgoing'])
                for x in months],
            months_len
        )

    s += "dues needed\n"

    # Which membership numbers do we want to see needed fees for?
    members_count = set([17, 30])
    # add in some of the average member numbers
    members_count.add(result['Average']['members'])
    members_count.add(result['MonthTD']['members'])

    for members in sorted(members_count):
        s += grid_render_onerow(
            " members {}".format(members), tags_len,
            [dues_given_members_outgoing(members, result[x]['outgoing'])
                for x in months],
            months_len
        )

    s += "\nNote: Total column does not include MonthTD numbers\n"

    return ''.join(s)


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
    'json_payments': {
        'func': subp_json_payments,
        'help': 'Output JSON of incoming payments',
    },
    'stats': {
        'func': subp_stats,
        'help': 'Output finance stats report',
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
                           default=os.path.join(os.path.join(
                               os.path.dirname(__file__), FILES_DIR)),
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

    args = argparser.parse_args()

    if not os.path.exists(args.dir):
        raise RuntimeError('Directory "{}" does not exist'.format(args.dir))

    # first, load the data
    args.rows = RowSet()
    args.rows.append(parse_dir(args.dir))

    # optionally split multi-month transactions into one per month
    if args.split:
        args.rows = args.rows.autosplit()

    # apply any filters requested
    args.rows = args.rows.filter(args.filter)

    result = args.func(args)
    print(result)
