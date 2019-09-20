#!/usr/bin/env python
# Licensed under GPLv3
import decimal
import re
import os
import glob

from row import Row


class RowSet(object):
    """Contain a bunch of rows, allowing statistics to be done on them
    """

    def __init__(self):
        self.rows = []
        self.balance = decimal.Decimal(0)

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
            if isinstance(row, (Row, RowSet)):
                sum += row.value
            else:
                raise ValueError("unexpected type")

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

        require_balance_line = False
        if len(self) > 0 and not skip_balance_check:
            # If we already have data in the rowset, then the first line of the
            # incoming file must be a balance line
            require_balance_line = True

        opening_balance = 0

        line_number = 0
        for row in stream.readlines():
            row = row.rstrip('\n')
            line_number += 1

            if not row:
                # Skip blank lines
                continue

            if re.match(r'^#', row):
                # TODO
                # - add comments and pragmas into the rows array for 100%
                #   round-triping
                match = re.match(r'^#balance ([-0-9.]+)', row)
                if match:
                    require_balance_line = False
                    given_balance = decimal.Decimal(match.group(1))
                    current_balance = opening_balance+self.balance
                    if len(self.rows) == 0:
                        # if the balance pragma is before any transaction
                        # data then it sets the opening balance for the set
                        opening_balance = given_balance
                        continue
                    elif given_balance != current_balance:
                        raise ValueError(
                            '{}:{} Failed to balance - expected {} but calcul'
                            'ated {}'.
                            format(
                                filename,
                                line_number,
                                given_balance,
                                current_balance
                            )
                        )
                # - in future there might be additional meta/pragmas
                # skip adding comment or meta lines
                continue

            if require_balance_line:
                raise ValueError(
                    '{}: trying to load a file that does not start with a'
                    'balance pragma'.format(filename)
                )

            try:
                self.append(Row.fromTxt(row))
            except: # noqa
                print("{}:{} Syntax error".format(filename, line_number))
                raise

    def load_directory(self, dirname, skip_balance_check=False):
        """Given the pathname to a directory, load all the relevant files found
        """

        # which files are relevant
        pattern = "*.txt"

        # sort the list so that we always load with matching balances
        files = sorted(glob.glob(os.path.join(dirname, pattern)))

        for filename in files:
            self.load_file(filename, skip_balance_check)

    def save_file(self, stream):
        """Given an open file handle, output the rowset in a format that can
           be loaded by load_file()
        """

        for row in self.rows:
            stream.write(str(row))
            stream.write("\n")

        return stream

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
                    key = None
                else:
                    # FIXME - Hack!
                    # - the "month" attribute of the row is intended for string
                    #   pattern matching, but the rowset wants to keep the
                    #   original objects intact as much as possible
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
