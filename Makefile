# this target is kept for a short time for historical purposes
balance: pages

# Generate the output into the pages directory, ready for publishing with
# something like github pages
#
.PHONY: pages
pages:
	mkdir -p pages
	python balance.py --split make_balance > pages/index.html
	python balance.py --split json_payments > pages/payments.json
	cp docs/pressstart2p.ttf pages
	$(MAKE) report > pages/report.txt

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
            echo Run git push --force origin master or similar; \
            false; \
	fi
	@cd pages; git remote add origin https://$(GITHUB_TOKEN)@github.com/dimsumlabs/dsl-accounts-pages
	curl https://github.com/dimsumlabs/dsl-accounts-pages
	cd pages; git push --force origin master:master

report:
	git describe --always --dirty
	@echo
	./balance.py --split grid
	@echo
	./balance.py --split --filter 'month>2016-08' --filter 'month!=2017-07' stats


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
	./run_tests.py

# Test to check that the code is able to sum the data in cash/* without crashing
test.sum:
	./balance.py sum

# run the unit tests and additionally produce a test coverage report
cover:
	./run_tests.py cover

cover.percent:
	coverage report --fail-under=100

clean:
	rm -rf htmlcov .coverage docs/index.html docs/payments.json docs/report.txt
