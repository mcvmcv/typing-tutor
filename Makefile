PY := .venv/bin

.PHONY: help install run test coverage lint format typecheck check app

help:
	@echo "make install    set up the virtualenv with the app and dev tools"
	@echo "make run        start the app"
	@echo "make test       run the tests"
	@echo "make coverage   run the tests with a coverage report"
	@echo "make lint       check style with ruff"
	@echo "make format     reformat the code with ruff"
	@echo "make typecheck  check types with mypy"
	@echo "make check      everything CI runs: lint, format check, types, tests"
	@echo "make app        build a standalone app in dist/ (no Python needed to run it)"

install:
	python3 -m venv .venv
	$(PY)/pip install -e ".[dev]"

run:
	$(PY)/python -m typing_tutor

test:
	$(PY)/pytest -q

coverage:
	$(PY)/pytest -q --cov --cov-report=term --cov-fail-under=90

lint:
	$(PY)/ruff check typing_tutor tests

format:
	$(PY)/ruff format typing_tutor tests
	$(PY)/ruff check --fix typing_tutor tests

typecheck:
	$(PY)/mypy

check: lint typecheck
	$(PY)/ruff format --check typing_tutor tests
	$(PY)/pytest -q --cov --cov-report=term --cov-fail-under=90

app:
	$(PY)/pip install -q -e ".[build]"
	$(PY)/pyinstaller --noconfirm packaging/learn-typing.spec
	QT_QPA_PLATFORM=offscreen dist/LearnTyping --smoke-test
