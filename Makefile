balance:
	cat docs/head.html > docs/index.html
	./balance_lite >> docs/index.html
	cat docs/foot.html >> docs/index.html
