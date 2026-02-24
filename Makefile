.PHONY: install test run clean

install:
	pip install -r requirements.txt

test:
	python test_clade.py

run:
	python claude.py

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete