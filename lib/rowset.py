# Licensed under GPLv3
import decimal
import os
import sys
import glob

from row import Row
from row import RowPragmaBalance
from row import RowData


class RowSet(object):
    """Contain a bunch of rows, allowing statistics to be done on them
    """

    def __init__(self):
        self.rows = []
        self.balance = decimal.Decimal(0)
        self.isforecast = False

    def __getitem__(self, i):
        return self.rows[i]

    def __len__(self):
        return len(self.rows)

    def __str__(self):
        s = ""
        for entry in self.rows:
            s += str(entry) + "\n"
        return s

    @property
    def value(self):
        sum = decimal.Decimal(0)
        for row in self:
            sum += row.value

        if self.balance != sum:
            raise ValueError("here {} {}".format(self.balance, sum))

        # ensure that values that have been promoted to have some digits
        # of significance return to being simple integers when possible.
        if int(sum) == sum:
            sum = sum.to_integral_exact()

        return sum

    def _add_one_value(self, item):
        """Given an object that looks like a Row, add its data to our current set
        """
        # FIXME
        # - if new rowset has an opening balance, it /MUST/ match the current
        #   blaance of the current rowset!!!
        self.rows.append(item)
        self.balance += item.value
        # TODO
        # - since we are recording cash values, it doesnt make sense for the
        #   balance to ever fall below zero.  Consider making that an fatal
        #   error here

        # if we incorporate any uncertain future forecast data, taint the
        # whole rowset with this status
        if item.isforecast:
            self.isforecast = True

    # TODO
    # - implement a "merge two RowSets" and ensure that it checks the
    #   closing/opening balances for compatibility with each other.
    #   Then use this function in the parse_dir() instead of manually
    #   itterating the entries. (Remember, this will force data load
    #   ordering requirements too)

    def append(self, item):
        """Given an object append it opaquely to our data as a single Row
        """
        if isinstance(item, (Row, RowSet)):
            self._add_one_value(item)
        elif isinstance(item, list):
            for entry in item:
                self._add_one_value(entry)
        else:
            raise ValueError('dont know how to append {}'.format(item))

    def load_file(self, stream, skip_balance_check=False):
        """Given an open file handle, read Row lines into this RowSet
        """
        if isinstance(stream, str):
            filename = stream
            stream = open(filename, 'r')
        else:
            filename = '(stream)'
        line_number = 0

        need_balance = True

        # TODO
        # - if we are loading just one file from a whole dir, its opening
        #   balance will need to be added to any calculated balance to avoid
        #   errors

        if skip_balance_check:
            need_balance = False

        last_error = None
        for row in stream.readlines():
            row = row.rstrip('\n')
            line_number += 1

            try:
                obj = Row.fromTxt(row)
            except Exception as e:
                print("{}:{} Syntax error".format(filename, line_number), file=sys.stderr)
                last_error = e

            if isinstance(obj, RowPragmaBalance):
                # TODO - move more of the pragma logic in to the pragma class

                if obj.balance != self.balance:
                    raise ValueError(
                        '{}:{} Failed to balance - expected {} but calcul'
                        'ated {}'.
                        format(
                            filename,
                            line_number,
                            obj.balance,
                            self.balance
                        )
                    )

                need_balance = False

            if isinstance(obj, RowData) and need_balance:
                raise ValueError(
                    '{}: trying to load a file that does not start with a'
                    ' balance pragma'.format(filename)
                )

            self.append(obj)

        if last_error is not None:
            print("Error: at least one syntax error. Trace is from last", file=sys.stderr)
            raise last_error

    def load_directory(self, dirname, skip_balance_check=False):
        """Given the pathname to a directory, load all the relevant files found
        """

        # which files are relevant
        pattern = "*.txt"

        # sort the list so that we always load with matching balances
        files = sorted(glob.glob(os.path.join(dirname, pattern)))

        for filename in files:
            self.load_file(filename, skip_balance_check)

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

    def filter_forecast(self):
        """Attempt to remove forecast lines that have a matching actual line"""
        # We define buckets of transactions with same month and same tag.
        # If there is exactly one forecast and one or more actual tranactions
        # we assume the forecast hae been met and remove it.
        #
        # TODO:
        # - These rules say that if there is multiple forecasts then we can
        #   never automatically remove them all - this is clearly wrong, but
        #   was useful to clearly show the dataset.  It needs fixing!
        # - The above definition does not cover all use cases
        #   E.G: multiple members donate small amounts each month, but they
        #   are all considered in the one tag
        # - Could conceivably want a different bucket definition
        # - The original ordering of the rowset is completely destroyed
        # - Since this destroys data, there should be a way to stop it from
        #   running twice on the same data

        result = RowSet()
        for month in self.group_by('month').values():
            for tag in month.group_by('hashtag').values():

                if not tag.isforecast:
                    result.append(list(tag))
                    continue

                split = tag.group_by('isforecast')

                if len(split[True]) != 1:
                    # there is more than one forecast item, dont filter
                    result.append(list(tag))
                    continue

                if False not in split:
                    # There are no real items, dont filter
                    result.append(list(tag))
                    continue

                # it looks like we have good data to replace the forecast
                result.append(list(split[False]))

        return result

    def autosplit(self):
        """look at the split bangtag and return the rowset all split
        """
        result = RowSet()
        for row in self:
            result.append(row.autosplit())
        return result

    def _split_locn_xfer(self):
        """look at the locn bangtag and return the rowset all split
        """
        # TODO:
        # - this could be cleaner, it is essentially breaking the promise of
        #   "auto" in the autosplit() above

        result = RowSet()
        for row in self:
            result.append(row._split_locn_xfer())
        return result

    def group_by(self, field):
        """Group the rowset by the given row field and return groups as a dict
        """
        # This could be cached for performance, but for clarity it is not
        result = {}
        for row in self:
            if field == 'month':
                if row.date is None:
                    # FIXME - Hack!
                    # If we have no date, then we cannot be grouped by that!
                    continue

            key = getattr(row, field, 'unknown')
            if key is None:
                key = 'unknown'

            if key not in result:
                result[key] = RowSet()

            result[key].append(row)
        return result

    def grid_by(self, field_x, field_y):
        """Group the rowset into a grid by the given two fields and return
        a grid object"""

        grid = RowGrid()
        grid.load_RowSet(field_x, field_y, self)

        return grid

    def last(self):
        """Return the chronologically last row from the rowset
        """
        def keyfn(row):
            return row.date

        return max(self, key=keyfn)


class RowGrid(object):
    """Contain a grid of rows.  E.G: grouped by both category and month"""

    def __init__(self):
        self.original_rows = []
        self.field_x = None
        self.field_y = None
        self._headings_x = {}
        self.rows = {}
        self.isforecast = False

    def _add_row(self, row):
        """Add a single row entry into the grid"""

        # TODO: DRY, getattr or unknown
        value_x = getattr(row, self.field_x, 'unknown')
        if value_x is None:
            value_x = 'unknown'

        value_y = getattr(row, self.field_y, 'unknown')
        if value_y is None:
            value_y = 'unknown'

        if value_x not in self._headings_x:
            self._headings_x[value_x] = RowSet()

        self._headings_x[value_x].append(row)

        # TODO: should there be a RowSetDict as well as the current RowSet
        #       array?
        if value_y not in self.rows:
            self.rows[value_y] = {}
        if value_x not in self.rows[value_y]:
            self.rows[value_y][value_x] = RowSet()

        self.rows[value_y][value_x].append(row)

        if row.isforecast:
            self.isforecast = True

    def load_RowSet(self, field_x, field_y, rowset):
        """Load a RowSet into the grid"""
        self.field_x = field_x
        self.field_y = field_y

        for row in rowset:
            self._add_row(row)

    @property
    def headings_x(self):
        """Return the key for each of the headings in the x direction"""

        return self._headings_x.keys()

    @property
    def headings_y(self):
        return self.rows.keys()

    @property
    def headings_y_width(self):
        """How wide do we need to make a column to fit all the y headings?
        mostly intended as a helper for jinja templates.
        """

        return max([len(i) for i in self.headings_y])

    def headings_x_format(self, method, arg):
        """Return a list of strings generated with the given method name
        mostly intended as a helper for jinja templates.
        """

        result = []
        for header in self.headings_x:
            fn = getattr(header, method)
            result.append(fn(arg))

        return result
