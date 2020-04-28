# by default, spit out a quick report
.PHONY: all
all: report

cashfiles := $(wildcard cash/*.txt)
cashfuturefiles := $(wildcard cash/future/*.txt)

# Generate the output into the pages directory, ready for publishing with
# something like github pages
#
.PHONY: pages
pages: pages/index.html pages/payments.json pages/stats.tsv
pages: pages/transactions.csv
pages: pages/pressstart2p.ttf
pages: pages/report.txt
pages: pages/report.future.txt
pages: pages/report_location.txt

pages/pressstart2p.ttf: docs/pressstart2p.ttf
	cp $< $@

pages/index.html: ./balance.py docs/template.html.j2 $(cashfiles)
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

pages/report.future.txt: ./balance.py $(cashfiles) $(cashfuturefiles)
	@mkdir -p pages
	$(MAKE) report.future >$@

pages/report_location.txt: ./balance.py $(cashfiles)
	@mkdir -p pages
	$(MAKE) report.location >$@

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
	./balance.py --split --filter 'rel_months>-20' stats
	@echo

report: report.describe report.grid report.stats

report.future:
	git describe --always --dirty
	@echo
	./balance.py --includefuture grid --filter_hack 410
	@echo

report.location: report.describe
	./balance.py report_location

docker:
	docker build -t dsl-accounts .
	docker run --rm dsl-accounts

build-dep:
	apt-get install flake8 python3-coverage python3-mock python3-jinja2

# Perform all available tests
.PHONY: test
test: test.code test.data

.PHONY: test.code
test.code: test.code.style test.code.units

# Test just the code style - note: much slower than the unit tests
.PHONY: test.code.style
test.code.style:
	flake8

# Test the correctness and sanity of the code with unit tests
.PHONY: test.code.units
test.code.units:
	TZ=UTC ./run_tests.py

.PHONY: test.data
test.data: test.data.doubletxn test.data.sum report.location

# Test to check that there are not two payments for the same tag in the same month
.PHONY: test.data.doubletxn
test.data.doubletxn:
	./balance.py check_doubletxn

# Test to check that the code is able to sum the data in cash/* without crashing
.PHONY: test.data.sum
test.data.sum:
	./balance.py sum

# run the unit tests and additionally produce a test coverage report
cover:
	TZ=UTC ./run_tests.py cover

cover.percent:
	coverage report --fail-under=100

clean:
	rm -rf htmlcov .coverage docs/index.html docs/payments.json docs/report.txt
