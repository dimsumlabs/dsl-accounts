#!/usr/bin/env python
# Licensed under GPLv3
import decimal
import types

from row import Row


class RowSet(object):
    """Contain a bunch of rows, allowing statistics to be done on them
    """

    def __init__(self):
        self.rows = []

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

        # ensure that values that have been promoted to have some digits
        # of significance return to being simple integers when possible.
        if int(sum) == sum:
            sum = sum.to_integral_exact()

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
