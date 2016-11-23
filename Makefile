balance:
	python balance.py --split make_balance > docs/index.html

build-dep:
	apt-get install python-coverage

# Perform all available tests
test: test.style test.units test.sum

# Test just the code style - note: much slower than the unit tests
test.style:
	flake8 ./*.py

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
	rm -rf htmlcov .coverage
