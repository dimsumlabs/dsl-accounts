The system will read the data in from one or more "cash files".  By default,
it will load all the `"cash/*.txt"` files.

These files are in a simple whitespace separated format.  For simplicity, it
is expected that there is one file for each month, but the code does not
require that layout.

# Basic format

Each line has the same basic format:

```
$value $record_date $comment
```

| Field | Description |
| ----- | ----------- |
| value | The value of this transaction.  Positive numbers are payments in to DimSumLabs, negative numbers are payments out from DimSumLabs |
| record_date | This is the date that we became aware of this transaction.  It may not be the effective date (ie: some bills are payed in arrears and we encourage club members to pay dues in advance) |
| comment | The remainder of the line becomes the comment - this may include some additional metadata (described below)

The first two columns are whitespace separated and the entire remainder of
the line becomes the comment - including any additional whitespaces.

# Additional Metadata

There are two ways that additional metadata can be supplied.

## Pragmas

Pragmas take affect during the loading of the file.

| Pragma | Description |
| ------ | ----------- |
| `#balance` | This pragma specifies the current balance of the accounts.  If, at the time of loading, the calculated balance does not match then an error is raised |

## Row tags

Row tags are applied on a per row basis and may not take affect until the
relevant row is processed in a specific way.

### Hash Tags

Each row can have one category applied to it.  The hashtag is simply some
text preceeded by a `#` and containing no whitespace.  These categories are
used to put transactions into buckets for reporting.


### Bang Tags

Bang tags affect the way that a row is processed.  They are a short text
string preceeded by a `!` and may be followed by one ore more colon separated
parameters.

| bangtag | parameters | description |
| ------- | ---------- | ----------- |
| `!months` | $number | Split this row into $number new rows over the same number of months, each one containing a fraction of the value (rounded down, with the remainder paid to the first month) - this is often used to record an advance payment for a year long service, where we want the effective date to be once per month |
| `!months` | $offset:$number | Similar to the one-parameter version, this first offsets the effective month by the offset - allowing back-dated effective dates or advance payments for a month in the future |
| `!months` | `child` | This tag is internally generated when splitting lines with the above months tags - it helps mark a line as a child of a split and will cause an error if an import is attempted |
| `!id` | $type:$value | If we have a unique transaction id for this entry, it should be recorded with this tag, making it available for automated processing |
| `!forecast` |  | Marks this line as a guess about the future - some outputs will show anything that includes forecast data with a `~` prefix |
| `!forecast` | `monthly` | Repeats the forcast monthly (currently stopping 6 months from 'now') |
| `!forecast` | `monthly:until:`$date | Repeats until the end date |
| `!locn` | $location | Assigns a location for this transaction (eg, "cashbox" or "paypal" or "bank_albert" |
| `!locn_xfer` | $from:$to:$amount | Transfers balance from one location to another (note the transaction must balance, so the row value must be zero) |

### Validating the tags

While the hash tags are free-form text, there is a list of valid tags.  The
bang tags only accept known values.  Using a tag outside of this list will
result in a consistancy check error.

TODO - the list of valid tags is hardcoded in the lib/row.py and should be
loaded from an external file.  This document could then record where to find
the external file so that users can understand what tags are available.

# Recording expected future transactions

In order to help with forecast of future financial status, there is an
option for loading more cash files from a second directory.  If the
`---includefuture` option is given to the balance.py command, it will
load files from `"cash/future/*.txt"` (It also relaxes the `#balance`
pragma checks for these files)

It is expected that these files will all include transactiosn tagged
with one of the `!forcast` bang tag variants.

When recording an expected monthly transaction, the record_date used
should normally be the date that this reoccuring transaction started
(even if this is in the past) - if a minor change (say, to the wording
or the "until" date) occurs, then there is no need to change the
record_date.

The record_date therefore becomes a simple proxy for the "start of
membership" or when the "service contract start date"

(For simple payments, with one transaction per month, there is logic
to remove the forecast payment when the real payment is recorded)
