.PHONY: test clean install run

# Run the tests
test:
	python -m unittest discover tests

# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete

# Install the package
install:
	pip install -e .

# Run the server with default settings
run:
	python share_website.py

# Build a distribution package
dist: clean
	python setup.py sdist bdist_wheel

# Upload to PyPI (requires twine)
upload: dist
	twine upload dist/*
