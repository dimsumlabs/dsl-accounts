[![Build Status](https://github.com/dimsumlabs/dsl-accounts/actions/workflows/ci.yml/badge.svg)](https://github.com/dimsumlabs/dsl-accounts/actions)

This repository keeps track of the DimSumLabs accounting.  We want to put
as much as possible of our internal working out in the open for all to see.
So, all the normal monthly expenses are visible via this repository.

It's not a double-entry accouting system, but simple text files to give us some
cashflow information, KISS style.

Patches welcome, let's keep it so simple that we'll actually do it! :)

It includes both the python code to generate reports, check consistancy and
output webpages as well as the actual data for our finances.

The transactions are all in a very simplistic text file, formated with
whitespace separated columns in the "cash" subdirectory.

After any changes are committed, the Continuous Integration system will
run checks and tests to be sure that everything looks ok.

You can run the same tests locally, so you can be sure that your changes
will pass:

```
make test
```

You can also see a simple report from the system:

```
make report
```

In order to run the above commands, you will need to have installed pip on your
device and then install the following libraries:
```
pip install flake8 coverage jinja2 pytz
```


## Checklist for transactions

* Add your transaction(s) in the appropriate `cash/YYYY-MM.txt`. Please maintain
  the existing *cash accounting basis*, i.e. the transaction date should be the
  date the cash was received/sent. *Do not* enter transactions in accrual basis;
  if the transaction is for another month, use the `!months:<start>:count>` tag.

* Run `make test`, which will apply several checks and print a summary.
    * Also check that the displayed account balances are consistent with reality.

* After large edits, consider running `make report.future` and see if there are any
  inconsistencies between past, current and forecast entries.
  The forecasts are loaded from `cash/future`.

* Commit and upload.
