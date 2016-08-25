balance:
	cat docs/head.html > docs/index.html
	python balance.py sum >> docs/index.html
	cat docs/foot.html >> docs/index.html
