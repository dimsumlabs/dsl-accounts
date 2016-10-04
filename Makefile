balance:
	python balance.py sum | cat docs/head.html - docs/foot.html > docs/index.html


build-dep:
	apt-get install python-coverage


# Test the correctness and sanity of the code
test:
	./run_tests.py

cover:
	./run_tests.py cover

clean:
	rm -rf htmlcov .coverage

