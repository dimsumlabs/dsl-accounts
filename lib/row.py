# Licensed under GPLv3
import datetime
import calendar
import decimal
import re


# TODO
# - make Row take Date objects and not strings with dates, removing a string
#   handling fart from Row.autosplit() and removing external formatting
#   knowledge from Row
# - The "!months:[offset:]count" tag is perhaps a little awkward, find a
#   more obvious format (perhaps "!months=month[,month]+" - which is clearly
#   a more discoverable format, but would get quite verbose with yearly
#   transactions (or even just one with more than 3 months...)


class Row:
    # This is used for compatibility with the old named tuple object
    # it is only used in the CSV handling.
    # TODO - change the way CSV works and remove this
    _fields = ['value', 'date', 'comment']

    def __init__(self, value=None, date=None, comment=None):
        if value is not None:
            value = decimal.Decimal(value)

        if date is not None:
            date = datetime.datetime.strptime(date.strip(), "%Y-%m-%d").date()

        self.value = value
        self.date = date
        self.comment = comment

        # Look at the comment for this row and extract the various types of
        # tags found.
        # hashtags are used to tag the category of each transaction and
        # might be overwritten later to decorate them nicely
        # bangtags are metainstructions to the parser
        self.hashtag = self._xtag('#')
        self.bangtag = self._xtag('!')

    # Implement len and getitem so that this object can be used with the
    # csv writer.
    # TODO - handle csv row creation within the row class and remove these
    def __len__(self):
        return len(self._fields)

    def __getitem__(self, i):
        attr = self._fields[i]
        return getattr(self, attr)

    # Implement equality test with other Row objects
    # This is used in the test_autosplit
    # TODO - implement the test differently and remove this
    def __eq__(self, other):
        return (
            self.__class__ == other.__class__ and
            self.value == other.value and
            self.date == other.date and
            self.comment == other.comment
        )

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
        now = datetime.datetime.now().date()
        month_this = self.date.replace(day=1)
        month_now = now.replace(day=1)
        rel_days = (month_this - month_now).days

        # approximate the relative number of months with 28 days per month.
        # for large enough relative values, this will be inaccurate.
        # TODO - improve the accuracy when needed
        return int(rel_days / 28.0)

    def _xtag_validate(self, x, tag):
        """Check the tag against valid tag names
        """

        # TODO:
        # load these lists from a file

        valid = {
            '#': [
                'bills:br',
                'bills:electricity',
                'bills:internet',
                'bills:meetup',
                'bills:rent',
                'bills:upkeep',
                'bills:water',
                'bookshelves',
                'donation',
                'donation:c3',
                'donation:members',
                'dues:[a-z][a-z0-9]*',
                'fees:paypal',
                'fridge',
                'loan',
                'merch:[a-z][a-z0-9]*',
                'supporters',
                'test_hashtag',
                'workshop',
            ],
            '!': [
                'months:[-0-9]+(:[0-9]+)?',
                'test_bangtag',
            ],
        }

        if x not in valid:
            raise ValueError("Unknown tag type {}".format(x))

        # TODO: constructing the regex could be optimised ..
        items = []
        for i in valid[x]:
            items.append('(^' + i + '$)')
        regex = '|'.join(items)
        p = re.compile(regex)

        if p.match(tag) is None:
            raise ValueError("Unknown tag {}{}".format(x, tag))

    def _xtag(self, x):
        """Generically extract tags with a given prefix
        """
        p = re.compile(x+r'([a-zA-Z]\S*)')
        all_tags = p.findall(self.comment)

        for tag in all_tags:
            self._xtag_validate(x, tag)

        # FIXME - enforce known case on all tags

        # TODO - have a better plan for what to do with multiple tags
        if len(all_tags) > 1:
            raise ValueError('Row has multiple {}tags: {}'.format(x, all_tags))

        if len(all_tags) == 0:
            return None

        return all_tags[0]

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
        tag = self.bangtag
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

        # TODO:
        # - mark the new split children to show that something has happend
        #   to this row

        # divide the value amongst all the child rows
        count_children = len(dates)
        if count_children < 1:
            raise ValueError(
                'would divide by zero, splitting children from {}'.format(
                    self.date))

        each_value = self.value / count_children
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
            remainder = self.value - each_value * count_children

            for date in dates:
                datestr = date.isoformat()
                this_value = each_value + remainder
                remainder = 0  # only add the remainder to the first child
                rows.append(Row(this_value, datestr, self.comment))

        # elif method == 'proportional':
        #   # The 'proportional' splitting attempts to pro-rata the transaction
        #   # value.  If the transaction is recorded 20% through the month then
        #   # only 80% of the monthly value is placed in that month.  The
        #   # rest is carried over into the next month, and so on.  This is
        #   # carried on until there is a month without enough value for the
        #   # whole month.  This final month is accorded the remaining amount.
        #   # Finally, the amount for the final month is converted to
        #   # a percentage, which is used to approximate a "end date".
        #   #
        #   # The hope is that this "end date" is good enough to be used as
        #   # a data source for membership end dates, but neither analysis nor
        #   # discussion has been done on this.
        #   #
        #   # TODO
        #   # - the code has rotted - it depends on calling Row() with
        #   #   the old direction arg
        #
        #   value = self.value  # the total value available to share
        #
        #   # for first month, only add the cash for the remainder of the month
        #   date = dates.pop(0)
        #   day = date.day
        #   percent = 1-min(28, day-1)/28.0  # FIXME - month lengths vary
        #   datestr = date.isoformat()
        #   this_value = int(each_value * percent)
        #   value -= this_value
        #   rows.append(Row(this_value, datestr, comment, self.direction))
        #
        #   # the body fills full months with full shares of the value
        #   while value >= each_value and len(dates):
        #       date = dates.pop(0)
        #       datestr = date.isoformat()
        #       value -= each_value
        #       rows.append(Row(each_value, datestr, comment, self.direction))
        #
        #   # finally, add any remainders
        #   if len(dates):
        #       date = dates.pop(0)
        #   else:
        #       date = self._month_add(date, 1)
        #   datestr = date.replace(day=1).isoformat()  # NOTE: clamp to 1st day
        #   # this will include any money lost due to rounding
        #   this_value = abs(sum(rows) - self.value)
        #   percent = min(1, this_value/each_value)
        #   day = percent * 27 + 1  # FIXME - month lengths vary
        #   week = int(day/7)
        #   comment += "({}% dom={} W{})".format(percent, day, week)
        #   # FIXME - record the resulting "end date" somewhere
        #   rows.append(Row(this_value, datestr, comment, self.direction))

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
        elif op == '!~':
            if not re.search(value_match, value_now, re.I):
                return self
        else:
            raise ValueError('Unknown filter operation "{}"'.format(op))

        return None

    def __str__(self):
        """Output the same format as input file - allowing roundtripping"""
        return "{} {} {}".format(self.value, self.date, self.comment)
