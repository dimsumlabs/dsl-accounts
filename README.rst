.. image:: https://travis-ci.org/dimsumlabs/dsl-accounts.svg?branch=master
           :target: https://travis-ci.org/dimsumlabs/dsl-accounts?branch=master
.. image:: https://coveralls.io/repos/dimsumlabs/dsl-accounts/badge.svg?branch=master&service=github
           :target: https://travis-ci.org/dimsumlabs/dsl-accounts?branch=master

Hey! We need to keep better track of cash expenses and incomings.

To sort this out, we've set up a simple "cash log" as a public repo on GitHub:

	https://github.com/dimsumlabs/dsl-accounts

It's got a very simplistic tab separated format for keeping track of
transactions, and the idea is to have a public log of incoming and
outgoing cash to re-establish some visibility into the cashflow for DSL.

For this to work, we have to keep the lists updated. (It's not a
double-entry accouting system, but simple text files to give us some
cashflow information, KISS style).

Patches welcome, let's keep it so simple that we'll actually do it! :)

* dsl-accounts/

  * balance.py
  * cash

    * incoming-2016-08
    * outgoing-2016-08

::

    ~/dsl-accounts $ ./balance.py sum
    Sum:  8100

(The sum should be the balance in the petty cash box, useful for knowing
where we stand regarding rent, bills)

