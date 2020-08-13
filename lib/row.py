# Licensed under GPLv3
import datetime
import calendar
import decimal
import re


# TODO
# - The "!months:[offset:]count" tag is perhaps a little awkward, find a
#   more obvious format (perhaps "!months=month[,month]+" - which is clearly
#   a more discoverable format, but would get quite verbose with yearly
#   transactions (or even just one with more than 3 months...)
# - update Row __init__ to enforce that value is a number


class Row(object):
    """A generic row type"""

    @classmethod
    def fromTxt(cls, text):
        """Return a new object constructed from the given input text line"""

        # First, handle blank lines
        if not text:
            return Row()

        if text[0] == '#':
            return RowPragma.fromTxt(text)

        # TODO: enforce four digits for year and two digits for month and day

        (value, date, comment) = text.split(None, maxsplit=2)
        date = datetime.datetime.strptime(date.strip(), "%Y-%m-%d").date()

        return RowData(value, date, comment)

    def __str__(self):
        return ""

    def __add__(self, other):
        if isinstance(other, Row):
            other = other.value

        return self.value + other

    def __radd__(self, other):
        return self.__add__(other)

    def __init__(self):
        self.value = 0
        self.date = None
        self.comment = None
        self.direction = None
        self.hashtag = None
        self.month = None
        self.rel_months = None
        self.isforecast = False
        self.isdata = False
        self.location = None
        self.taxyearhk = None

    def _getvalue_simple(self, field):
        """return the field value as a simple number or string
        """
        attr = getattr(self, field)

        if isinstance(attr, (int, str, decimal.Decimal)):
            return attr

        if attr is None:
            return None

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

        if field == 'month':
            # HACK - months are datetime objects, but to compare with the
            # user supplied string, we need to strip off the date
            # - there is no similar hack in the match() method, should there?
            value_now = value_now[0:7]

        # FIXME TODO HACK
        # - the old _getvalue_simple always coerced None into str('None'),
        #   which was not the intention, however the re.search matches
        #   turn out to rely on that
        value_now_str = str(value_now)

        if op == '=~':
            if re.search(value_match, value_now_str, re.I):
                return self
            return None

        if op == '!~':
            if not re.search(value_match, value_now_str, re.I):
                return self
            return None

        if value_now is None:
            # FIXME TODO HACK
            # - python 2 silently compared str('None') to 0 and worked
            # - python 3 complains
            # - This code turns out to rely on the python 2 comparison
            # As a hack, if we detect this, pretend None is very negative
            value_now = float('-inf')

        # coerce our value to match into a number, if that looks possible
        try:
            value_match = float(value_match)
        except ValueError:
            pass

        if op == '==':
            if value_now == value_match:
                return self
            return None

        if op == '!=':
            if value_now != value_match:
                return self
            return None

        if op == '>':
            if value_now > value_match:
                return self
            return None

        if op == '<':
            if value_now < value_match:
                return self
            return None

        if op == '>=':
            if value_now >= value_match:
                return self
            return None

        if op == '<=':
            if value_now <= value_match:
                return self
            return None

        raise ValueError('Unknown filter operation "{}"'.format(op))

    def autosplit(self, method=None):
        return [self]

    def _split_locn_xfer(self):
        # TODO: this will be removed when the autosplit is refactored
        return [self]


class RowComment(Row):
    """A row containing a comment"""

    def __init__(self, comment):
        super().__init__()
        self.comment = comment

    def __str__(self):
        if self.comment:
            return '#' + self.comment
        return '#'


class RowPragma(Row):
    """A row containing a pragma command"""

    @classmethod
    def fromTxt(cls, text):
        if text[0] != '#':
            raise ValueError("Not a pragma or a comment: {}".format(text))

        if text[0:8] == '#balance':
            match = re.match(r'^#balance ([-0-9.]+)(\s+)?(.*)', text)
            if match:
                balance = match.group(1)
                comment = match.group(3)
                return RowPragmaBalance(balance, comment)

            raise ValueError("Syntax Error in balance pragma: {}".format(text))

        return RowComment(text[1:])

        # TODO
        # - extract params better


class RowPragmaBalance(RowPragma):
    """A row with the balance pragma"""

    # TODO
    # - move more of the pragma processing into this class

    def __init__(self, balance, comment):
        super().__init__()
        self.balance = decimal.Decimal(balance)
        self.comment = comment

    def __str__(self):
        string = '#balance {}'.format(self.balance)
        if self.comment:
            return string + ' ' + self.comment
        return string


class RowData(Row):
    """A row containing accounting data"""

    # This is used for compatibility with the old named tuple object
    # it is only used in the CSV handling.
    # TODO - change the way CSV works and remove this
    _fields = ['value', 'date', 'comment']

    def __str__(self):
        """Output the same format as input file - allowing roundtripping"""

        # the two manditory fields
        fields = [str(self.value), str(self.date)]

        comment = self.comment
        if comment:
            fields.append(comment)

        return ' '.join(fields)

    def __init__(self, value, date, comment):
        if not isinstance(date, datetime.date):
            raise ValueError("{} is not a date object".format(date))

        self.hashtag = None
        self.bangtags = dict()
        self.value = decimal.Decimal(value)
        self.date = date
        self.comment = comment
        self.isdata = True

        if 'months' in self.bangtags and 'forecast' in self.bangtags:
            raise ValueError('Cannot have both months and forecast bang tags')

    # Implement len and getitem so that this object can be used with the
    # csv writer.
    # TODO - handle csv row creation within the row class and remove these
    def __len__(self):
        return len(self._fields)

    def __getitem__(self, i):
        attr = self._fields[i]
        return getattr(self, attr)

    @property
    def direction(self):
        if self.value < 0:
            return "outgoing"
        else:
            return "incoming"

    @property
    def month(self):
        """representation of the date as the first of the month
           - used for the filter language
             (others should just use the date object)
        """
        return self.date.replace(day=1)

    @property
    def taxyearhk(self):
        """
            The tax year or year of assessment runs from 1 April of a year
            to 31 March of the following year.

            Return a string that clearly identifies the tax year this
            object is part of.
        """
        if self.date.month < 4:
            year = self.date.year
        else:
            year = self.date.year + 1

        return "ye{}".format(year)

    def category_prefix(self, level):
        """
            Truncate the category ("hashtag") at the given level

            This is used to summarise entire category groups:
            Eg:
                "bills:rent" at the level 1 prefix is "bills"
        """
        if level < 0:
            raise ValueError("a negative prefix is nonsense")
        return ':'.join(self.hashtag.split(':')[:level])

    @property
    def category_prefix1(self):
        # TODO: this is awkward, but it is simpler than allowing
        # parameters in the match() code
        return self.category_prefix(1)

    @property
    def rel_months(self):
        now = datetime.datetime.now().date()
        month_now = now.replace(day=1)
        rel_days = (self.month - month_now).days

        # approximate the relative number of months with 28 days per month.
        # for large enough relative values, this will be inaccurate.
        # TODO - improve the accuracy when needed
        return int(rel_days / 28.0)

    @property
    def comment(self):
        """Re-insert the tags into the comment"""
        tags = dict()
        if self.hashtag:
            tags['hashtag'] = '#'+self.hashtag

        for k, v in self.bangtags.items():
            fields = v.copy()
            fields.insert(0, k)
            tags['bangtag,'+k] = '!' + ':'.join(fields)

        return self._comment.format(**tags)

    @comment.setter
    def comment(self, newcomment):
        self._comment = newcomment

        # Look at the comment for this row and extract the various types of
        # tags found.
        # hashtags are used to tag the category of each transaction and
        # might be overwritten later to decorate them nicely
        # bangtags are metainstructions to the parser
        self._hashtag()
        self._bangtags()

    @property
    def isforecast(self):
        return ('forecast' in self.bangtags)

    @property
    def location(self):
        if 'locn' in self.bangtags:
            return self.bangtags['locn'][0]
        return None

    def _xtag_validate(self, x, tag):
        """Check the tag against valid tag names
        """

        # TODO:
        # load these lists from a file

        valid = {
            '#': [
                'bills:accounting',
                'bills:br',
                'bills:dns',
                'bills:electricity',
                'bills:hosting',
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
                'recycling',
                'supporters',
                'test_hashtag',
                'test_hashtag2(:.*)?',
                'workshop',
            ],
            '!': [
                'forecast(:.*)?',
                'id:paypal:[0-9ABCDEFGHJKLMNPRSTUVWXY]{17}',
                'id:cac:[0-9]+',
                'locn:gary',
                'locn:hamish',
                'locn:nic',
                'locn:paypal',
                'locn:philip',
                'locn:test_location',
                'locn:test_location2',
                'locn_xfer:.*',
                'months:[-0-9]+(:[0-9]+)?',
                'test_bangtag',
                'test_bangtag2(:.*)?',
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

        if self._comment is None:
            return None

        # TODO:
        # - should a tag char start a tag /anywhere/ in the string?
        # - how do we detect syntax errors like "xyz id!:paypal:foo abc"?

        p = re.compile(x+r'([A-Za-z:]\S*)')
        all_tags = p.findall(self._comment)

        for tag in all_tags:
            self._xtag_validate(x, tag)

        # FIXME - enforce known case on all tags

        return all_tags

    def _hashtag(self):
        """Extract any hashtag from the comment"""

        hashtags = self._xtag('#')
        if len(hashtags) > 1:
            raise ValueError('Row has multiple hashtags: {}'.format(hashtags))
        if not hashtags:
            return

        hashtag = hashtags[0]
        self.hashtag = hashtag

        self._comment = re.sub(r'#'+hashtag, '{hashtag}', self._comment)

    def _set_bangtag(self, tagname, args):
        """Set a bangtag property"""
        if tagname != tagname.lower():
            raise ValueError('bangtag {} is not lowercase'.format(tagname))
        if tagname in self.bangtags:
            raise ValueError('Row has multiple !{} tags'.format(tagname))

        # TODO:
        # - should args be a known case too?

        self.bangtags[tagname] = args

    def _bangtags(self):
        """Extract any bangtags from the comment"""

        bangtags = self._xtag('!')

        if not bangtags:
            return

        for bangtag in bangtags:
            fields = bangtag.split(':')
            tagname = fields.pop(0)

            self._set_bangtag(tagname, fields)

            # If this bangtag is in the original comment, ensure updates get
            # propogated back to it when rendered
            replacement = '{bangtag,'+tagname+'}'
            self._comment = re.sub(r'!'+bangtag, replacement, self._comment)

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
        if 'months' not in self.bangtags:
            return [self.date]

        fields = self.bangtags['months']

        if len(fields) < 1 or len(fields) > 2:
            raise ValueError('months bang must specify one or two numbers')

        if len(fields) == 2:
            # the fields are "start:count"
            start = int(fields[0])
            end = start+int(fields[1])
        else:
            # otherwise, the field is just "count"
            start = 0
            end = int(fields[0])

        dates = []
        for i in range(start, end):
            dates.append(self._month_add(self.date, i))

        return dates

    def _split_locn_xfer(self):
        """split a locn_xfer into a double-entry set.  Note that this
        /is/ a type of split, but not one that is done by autosplit.
        Only the report_location currently does this kind of split
        """
        # FIXME:
        # - DRY
        # - the child marker system is getting strained, needs refactor
        # - setting the location here is awkward too
        # - the split/autosplit/nosplit distinction is more blurry
        #   with this feature.  Fix this!

        if 'locn_xfer' not in self.bangtags:
            return [self]

        if self.value != 0:
            raise ValueError('locn_xfer unbalanced - '
                             'value is {}'.format(self.value))

        # TODO:
        # - validate the from and to location names as being from
        #   the list of allowed locations

        source = self.bangtags['locn_xfer'][0]
        dest = self.bangtags['locn_xfer'][1]
        amount = decimal.Decimal(self.bangtags['locn_xfer'][2])

        # FIXME: DRY
        row_source = RowData(-amount, self.date, self._comment)
        row_source.comment = self.comment + ' !locn:{}'.format(source)

        # mutate the bangtags to show this is a child
        row_source._set_bangtag('child', ['locn_xfer'])

        # FIXME: DRY
        row_dest = RowData(amount, self.date, self._comment)
        row_dest.comment = self.comment + ' !locn:{}'.format(dest)

        # mutate the bangtags to show this is a child
        row_dest._set_bangtag('child', ['locn_xfer'])

        return [row_source, row_dest]

    def _autosplit_forecast(self):
        """split forecast monthly reoccuring items into one for each month"""
        args = self.bangtags['forecast']

        if not args:
            # This is a singleton forecast line
            return None

        if args[0] != 'monthly':
            raise ValueError("Dont know how to handle forecast {}".format(
                args[0]))

        if len(args) > 1:
            if args[1] != 'until':
                raise ValueError("Dont know how to handle forecast:monthly {}"
                                 .format(args[1]))
            lastdate = datetime.datetime.strptime(
                    args[2].strip(), "%Y-%m-%d").date()
        else:
            lastdate = self._month_add(datetime.datetime.now().date(), 6)

        rows = []
        this = self.date
        while this <= lastdate:
            new = RowData(self.value, this, self._comment)
            if self.hashtag:
                new.hashtag = self.hashtag

            new.bangtags = self.bangtags.copy()

            # mutate the bangtags to show this is a child
            new.bangtags['forecast'][0] = 'child'

            rows.append(new)

            this = self._month_add(this, 1)

        return rows

    def autosplit(self):
        """look at the split bangtag and return a split row if needed
        """

        # TODO
        # - the autosplit is only used on RowSet objects, so remove all the
        #   infrastructure from Row and add it to RowSet

        rows = []

        if 'months' in self.bangtags:
            # we have a transaction to split

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
            # (force numbers that can be represented in cash by using int())
            each_value = int(each_value)

            # just divide the transaction value
            # amongst multiple months - rounding any fractions down
            # and applying them to the first month

            # no splitting needed, return unchanged
            if len(dates) == 1 and dates[0] == self.date:
                return [self]

            # the remainder is any money lost due to rounding
            remainder = self.value - each_value * count_children

            for date in dates:
                this_value = each_value + remainder
                remainder = 0  # only add the remainder to the first child
                new = RowData(this_value, date, self._comment)
                if self.hashtag:
                    new.hashtag = self.hashtag

                new.bangtags = self.bangtags.copy()

                # mutate the bangtags to show this is a child
                new.bangtags['months'] = ['child']

                rows.append(new)

            return rows

        if 'forecast' in self.bangtags:
            rows = self._autosplit_forecast()

        if not rows:
            return [self]

        return rows

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
