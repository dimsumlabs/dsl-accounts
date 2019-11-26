# Licensed under GPLv3
import decimal
import os
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
                print("{}:{} Syntax error".format(filename, line_number))
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
            print("Error: at least one syntax error. Trace is from last")
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
                if row.date is None:
                    # FIXME - Hack!
                    # If we have no date, then we cannot be grouped by that!
                    continue

            if hasattr(row, field):
                key = getattr(row, field)

            if key is None:
                key = 'unknown'

            if key not in result:
                result[key] = RowSet()

            result[key].append(row)
        return result

    def last(self):
        """Return the chronologically last row from the rowset
        """
        def keyfn(row):
            return row.date

        return max(self, key=keyfn)
