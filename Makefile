# by default, spit out a quick report
.PHONY: all
all: report

cashfiles := $(wildcard cash/*.txt)

# Generate the output into the pages directory, ready for publishing with
# something like github pages
#
.PHONY: pages
pages: pages/index.html pages/payments.json pages/stats.tsv
pages: pages/transactions.csv
pages: pages/pressstart2p.ttf
pages: pages/report.txt

pages/pressstart2p.ttf: docs/pressstart2p.ttf
	cp $< $@

pages/index.html: ./balance.py docs/template.html $(cashfiles)
	@mkdir -p pages
	./balance.py --split make_balance >$@

pages/transactions.csv: ./balance.py $(cashfiles)
	@mkdir -p pages
	./balance.py --nosplit csv >$@

pages/payments.json: ./balance.py $(cashfiles)
	@mkdir -p pages
	./balance.py --split json_payments >$@

pages/stats.tsv: ./balance.py $(cashfiles)
	@mkdir -p pages
	./balance.py --split statstsv >$@

pages/stats.pdf: stats.gnuplot pages/stats.tsv
	gnuplot stats.gnuplot

pages/report.txt: ./balance.py $(cashfiles)
	@mkdir -p pages
	$(MAKE) report >$@

# Replicate the travisCI deploy pages provider.
#
# This open-coded version is more understandable, more debuggable and
# more likely to be reusuable on other CI systems.
#
# But most importantly, it is not broken in some unfathomable way.
#
deploy: pages
	rm -rf pages/.git
	git init pages
	cd pages; git add -A .
	cd pages; git commit -m "Auto Deploy"
	@if [ -z "$(GITHUB_TOKEN)" ]; then \
            echo ERROR: no token found in environment, manual deploy required; \
            false; \
	fi
	@cd pages; git remote add origin https://$(GITHUB_TOKEN)@github.com/dimsumlabs/dsl-accounts-pages
	cd pages; git push --force origin master:master

report.describe:
	git describe --always --dirty
	@echo

report.grid:
	./balance.py --split grid --filter_hack 410
	@echo

report.stats:
	./balance.py --split --filter 'rel_months>-20' --filter 'month!=2017-07' stats
	@echo

report: report.describe report.grid report.stats

report.future:
	git describe --always --dirty
	@echo
	./balance.py --includefuture grid --filter_hack 410
	@echo

docker:
	docker build -t dsl-accounts .
	docker run --rm dsl-accounts

build-dep:
	apt-get install flake8 python-coverage python-mock

# Perform all available tests
test: test.style test.units test.sum

# Test just the code style - note: much slower than the unit tests
test.style:
	flake8 ./*.py lib/*.py

# Test the correctness and sanity of the code with unit tests
test.units:
	TZ=UTC ./run_tests.py

# Test to check that the code is able to sum the data in cash/* without crashing
test.sum:
	./balance.py sum

# run the unit tests and additionally produce a test coverage report
cover:
	TZ=UTC ./run_tests.py cover

cover.percent:
	coverage report --fail-under=100

clean:
	rm -rf htmlcov .coverage docs/index.html docs/payments.json docs/report.txt
