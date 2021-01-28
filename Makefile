PYTHON=python3

.PHONY: lint test
lint:
	flake8 cfde_submit tests
test:
	pytest

.PHONY: lint test
release: clean lint test
	$(PYTHON) setup.py sdist bdist_wheel

.PHONY: upload
upload: release
	twine check dist/*
	twine upload dist/*

.PHONY: testupload
testupload: release
	twine check dist/*
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

.PHONY: clean
clean:
	rm -rf dist build *.egg-info
