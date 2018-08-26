#!/usr/bin/env python
# Licensed under GPLv3
import decimal
import re


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
        self.rows.append(item)
        self.balance += item.value

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

    def load_file(self, stream):
        """Given an open file handle, read Row lines into this RowSet
        """
        if isinstance(stream, str):
            filename = stream
            stream = open(filename, 'r')
        else:
            filename = '(stream)'

        for row in stream.readlines():
            row = row.rstrip('\n')

            if not row:
                # Skip blank lines
                continue

            if re.match(r'^#', row):
                # skip comment lines
                # - in future there might be meta/pragmas
                continue

            # TODO - the row class should handle fields inside the line
            self.append(Row(*re.split(r'\s+', row, maxsplit=2)))

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
