# Makefile for running the Flask API

.PHONY: run

run:
	pipenv run python -m flask --app scraper/presentation/api run --host=0.0.0.0 --port=5000 --debug

.PHONY: lint
lint:
	pipenv run flake8 .

.PHONY: format
format:
	pipenv run black .

.PHONY: isort
isort:
	pipenv run isort .

.PHONY: check
check:
	pipenv run black --check . && pipenv run isort --check-only . && pipenv run flake8 .

.PHONY: clean
clean:
	find . -type d -name '__pycache__' -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache
