#!/usr/bin/env python
# Licensed under GPLv3
from collections import namedtuple
import datetime
import argparse
import calendar
import os.path
import decimal
import json
import sys
import csv
import os
import re
import types

#
# TODO
# - make Row take Date objects and not strings with dates, removing a string
#   handling fart from Row.autosplit() and removing external formatting
#   knowledge from Row
# - The "!months:[offset:]count" tag is perhaps a little awkward, find a
#   more obvious format (perhaps "!months=month[,month]+" - which is clearly
#   a more discoverable format, but would get quite verbose with yearly
#   transactions (or even just one with more than 3 months...)
# - if we convert subp_csv to write to - and return - a string, then we
#   can add a unit test for it.  We could also then turn the "--out"
#   option into a global one, which would be the output destination for
#   any command output
# - The Row object should allow a direction indicating "auto" to take
#   the direction from the sign of the value - this would simplify the
#   places where we automatically create a new Row (eg, from splitting)
# - Implement a running balance check - perhaps using pragma lines in
#   the input - then we can add a check that the calculated balance matches
#   the known counted balance at that point in time (quick, accounting people,
#   tell me the name for this concept!).  Complicating this is the fact that
#   the running balance is split accross two files - so, this might need
#   consolidate the incoming and outgoing files.


FILES_DIR = 'cash'

# Ensure we do not invent more money
decimal.getcontext().rounding = decimal.ROUND_DOWN


class Row(namedtuple('Row', ('value', 'date', 'comment'))):

    def __new__(cls, value, date, comment, direction):
        value = decimal.Decimal(value)
        date = datetime.datetime.strptime(date.strip(), "%Y-%m-%d").date()

        if direction not in ('incoming', 'outgoing'):
            raise ValueError('Direction "{}" unhandled'.format(direction))

        # We use the direction field, so it is impossible to have a negative
        # value
        if value < 0:
            raise ValueError('Value "{}" is negative'.format(value))

        # Inverse value
        if direction == 'outgoing':
            value = decimal.Decimal(0)-value

        obj = super(cls, Row).__new__(cls, value, date, comment)

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

    @property
    def direction(self):
        if self.value < 0:
            return "outgoing"
        else:
            return "incoming"

    @property
    def month(self):
        """a short string representation of the date as a month
           - used for the filter language
             (others should just use the date object)
        """
        return self.date.strftime('%Y-%m')

    @property
    def rel_months(self):
        now = datetime.datetime.utcnow().date()
        month_this = self.date.replace(day=1)
        month_now = now.replace(day=1)
        rel_days = (month_this - month_now).days

        # approximate the relative number of months with 28 days per month.
        # for large enough relative values, this will be inaccurate.
        # TODO - improve the accuracy when needed
        return int(rel_days / 28.0)

    def _xtag(self, x):
        """Generically extract tags with a given prefix
        """
        p = re.compile(x+'([a-zA-Z]\S*)')
        all_tags = p.findall(self.comment)

        # FIXME - enforce known case on all tags

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
        day = min(day, calendar.monthrange(year, month)[1])

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

    def autosplit(self, method='simple'):
        """look at the split bangtag and return a split row if needed
        """
        dates = self._split_dates()

        # append a bangtag to show that something has happend to this row
        # this also means that it cannot be passed to split() twice as that
        # would find two bangtags and raise an exception
        comment = self.comment+' !child'

        # divide the value amongst all the child rows
        count_children = len(dates)
        if count_children < 1:
            raise ValueError(
                'would divide by zero, splitting children from {}'.format(
                    self.date))

        # (The abs value is taken because the sign is in the self.direction)
        each_value = abs(self.value / count_children)
        # (avoid numbers that cannot be represented with cash by using int())
        each_value = int(each_value)

        rows = []

        if method == 'simple':
            # The 'simple' splitting will just divide the transaction value
            # amongst multiple months - rounding any fractions down
            # and applying them to the first month

            # no splitting needed, return unchanged
            if len(dates) == 1 and dates[0] == self.date:
                return [self]

            # the remainder is any money lost due to rounding
            remainder = abs(self.value) - each_value * count_children

            for date in dates:
                datestr = date.isoformat()
                this_value = each_value + remainder
                remainder = 0  # only add the remainder to the first child
                rows.append(Row(this_value, datestr, comment, self.direction))

        elif method == 'proportional':
            # The 'proportional' splitting attempts to pro-rata the transaction
            # value.  If the transaction is recorded 20% through the month then
            # only 80% of the monthly value is placed in that month.  The
            # rest is carried over into the next month, and so on.  This is
            # carried on until there is a month without enough value for the
            # whole month.  This final month is accorded the remaining amount.
            # Finally, the amount for the final month is converted to
            # a percentage, which is used to approximate a "end date".
            #
            # The hope is that this "end date" is good enough to be used as
            # a data source for membership end dates, but neither analysis nor
            # discussion has been done on this.

            value = self.value  # the total value available to share

            # for first month, only add the cash for the remainder of the month
            date = dates.pop(0)
            day = date.day
            percent = 1-min(28, day-1)/28.0  # FIXME - month lengths vary
            datestr = date.isoformat()
            this_value = int(each_value * percent)
            value -= this_value
            rows.append(Row(this_value, datestr, comment, self.direction))

            # the body fills full months with full shares of the value
            while value >= each_value and len(dates):
                date = dates.pop(0)
                datestr = date.isoformat()
                value -= each_value
                rows.append(Row(each_value, datestr, comment, self.direction))

            # finally, add any remainders
            if len(dates):
                date = dates.pop(0)
            else:
                date = self._month_add(date, 1)
            datestr = date.replace(day=1).isoformat()  # NOTE: clamp to 1st day
            # this will include any money lost due to rounding
            this_value = abs(sum(rows) - self.value)
            percent = min(1, this_value/each_value)
            day = percent * 27 + 1  # FIXME - month lengths vary
            week = int(day/7)
            comment += "({}% dom={} W{})".format(percent, day, week)
            # FIXME - record the resulting "end date" somewhere
            rows.append(Row(this_value, datestr, comment, self.direction))

        else:
            raise ValueError('unknown splitter method name')

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

    def _getvalue_simple(self, field):
        """return the field value as a simple number or string
        """
        attr = self._getvalue(field)

        if isinstance(attr, (int, str, decimal.Decimal)):
            return attr

        # convert all 'complex' types into string representations
        return str(attr)

    def match(self, **kwargs):
        """using kwargs, check if this Row matches if so, return it, or None
        """
        for key, value in kwargs.items():
            attr = self._getvalue_simple(key)
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
        value_now = self._getvalue_simple(field)

        # coerce our value to match into a number, if that looks possible
        try:
            value_match = float(value_match)
        except ValueError:
            pass

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


class RowSet(object):
    """Contain a bunch of rows, allowing statistics to be done on them
    """

    def __init__(self):
        self.rows = []

    def __getitem__(self, i):
        return self.rows[i]

    @property
    def value(self):
        sum = 0
        for row in self:
            if isinstance(row, (Row, RowSet)):
                sum += row.value
            else:
                raise ValueError("unexpected type")
        return sum

    def append(self, item):
        if isinstance(item, (Row, RowSet)):
            self.rows.append(item)
        elif isinstance(item, list):
            for entry in item:
                self.append(entry)
        elif isinstance(item, types.GeneratorType):
            # Yes, we could get fancy and store the generator and only
            # render it when we need to, but that would also need us to
            # take into account the correct ordering for all things
            # - so until our dataset is huge, just skip the fancy bits
            self.append(list(item))
        else:
            raise ValueError('dont know how to append {}'.format(item))

    def filter(self, filter_strings):
        """Apply the given list of human readable filters to the rows
        """
        if filter_strings is None:
            filter_strings = []

        result = RowSet()
        for row in self.rows:
            match = True
            for s in filter_strings:
                if not row.filter(s):
                    match = False
                    break
            if match:
                result.append(row)
        return result

    def autosplit(self):
        """look at the split bangtag and return the rowset all split
        """
        result = RowSet()
        for row in self:
            result.append(row.autosplit())
        return result

    def group_by(self, field):
        """Group the rowset by the given row field and return groups as a dict
        """
        # This could be cached for performance, but for clarity it is not
        result = {}
        for row in self:
            if field == 'month':
                # FIXME - Hack!
                # - the "month" attribute of the row is intended for string
                #   pattern matching, but the rowset wants to keep the original
                #   objects intact as much as possible
                key = row.date.replace(day=1)
            else:
                key = row._getvalue(field)

            if key is None:
                key = 'unknown'

            if key not in result:
                result[key] = RowSet()

            result[key].append(row)
        return result

    def last(self):
        """Return the chronologically last row from the rowset
        """
        rows = sorted(self, key=lambda x: x.date)
        return rows[-1]


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
                yield Row(*re.split(r'\s+', row,
                                    # Number of splits (3 fields)
                                    maxsplit=2),
                          direction=direction)


def render_month(date):
    """Return a short string representation of the date as a month
    """
    return date.strftime('%Y-%m')


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
    month_names = set()

    months = rows.group_by('month')
    for month in months:
        month_str = render_month(month)
        month_names.add(month_str)
        totals[month_str] = months[month].value

        tags = months[month].group_by('hashtag')

        for tag in tags:
            # I would prefer auto-vivification to all these if statements
            if tag not in grid:
                grid[tag] = {}

            grid[tag][month_str] = {}
            grid[tag][month_str]['sum'] = tags[tag].value
            grid[tag][month_str]['last'] = tags[tag].last().date

    totals['total'] = rows.value
    return month_names, grid, totals


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
    s.append("{:<{width}}".format('MONTH Sub Total', width=tags_len))

    for month in months:
        s.append("{:>{}}".format(totals[month], months_len))

    s.append("\n")
    s.append("{:<{width}}".format('RUNNING Balance', width=tags_len))

    running_total = 0
    for month in months:
        running_total += totals[month]
        s.append("{:>{}}".format(running_total, months_len))

    s.append("\n")
    s.append("TOTAL: {:>{}}".format(totals['total'], months_len))

    return s


def grid_render_rows(months, tags, grid, months_len, tags_len):
    s = []

    tags = sorted(tags)

    # Output each tag
    for tag in tags:
        row = ''
        row += "{:<{width}}".format(tag.capitalize(), width=tags_len)

        for month in months:
            if month in grid[tag]:
                col = grid[tag][month]['sum']
            else:
                col = ''
            row += "{:>{}}".format(col, months_len)

        row += "\n"
        s.append(row)

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


def subp_csv(args):  # pragma: no cover
    rows = RowSet()
    rows.append(sorted(args.rows, key=lambda x: x.date))

    with args.csv_out as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow([row.capitalize() for row in Row._fields])

        for row in rows:
            writer.writerow(row)

        writer.writerow('')
        writer.writerow(('Sum',))
        writer.writerow((rows.value,))
    return None


def subp_grid(args):
    # ensure that each category has a nice and clear prefix
    for row in args.rows:
        if row.hashtag is None:
            row.hashtag = 'unknown'

        if row.direction == 'outgoing':
            row.hashtag = 'out ' + row.hashtag
        else:
            row.hashtag = 'in ' + row.hashtag

    (months, grid, totals) = grid_accumulate(args.rows)
    tags = args.rows.group_by('hashtag').keys()

    return grid_render(months, tags, grid, totals)


def subp_json_payments(args):

    rows = args.rows.filter([
        'direction==incoming',
    ])

    (months, grid, totals) = grid_accumulate(rows)

    # We are only interested in last payment date
    return json.dumps(({
        k.lower(): sorted(
            v.keys(),
            key=lambda x: tuple(map(int, x.split('-')))
        )[-1] for k, v in grid.items()
    }))


def subp_make_balance(args):
    def _format_tpl(tpl, key, value):
        '''Poor mans template engine'''
        return tpl.replace(('{%s}' % key), value)

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

    tpl = _format_tpl(tpl, 'balance_sum', str(args.rows.value))
    tpl = _format_tpl(tpl, 'grid_header', header)
    tpl = _format_tpl(tpl, 'grid', grid)
    tpl = _format_tpl(tpl, 'rent_due', str(_get_next_rent_month()))

    return tpl


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
    args.rows = RowSet()
    args.rows.append(parse_dir(args.dir))

    # optionally split multi-month transactions into one per month
    if args.split:
        args.rows = args.rows.autosplit()

    # apply any filters requested
    args.rows = args.rows.filter(args.filter)

    result = args.func(args)
    if result is not None:
        print(result)
