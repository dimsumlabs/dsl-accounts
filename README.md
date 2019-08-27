[![Build Status](https://travis-ci.org/dimsumlabs/dsl-accounts.svg?branch=master)](https://travis-ci.org/dimsumlabs/dsl-accounts)

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

You can run the same tests localally, so you can be sure that your changes
will pass:

```
make test
```

You can also see a simple report from the system:

```
make report
```
