.PHONY: all test flake black mypy pytest venv

PYTHON=python3
VPYTHON=.venv/bin/python3
SRC=grf2txt

all: test

test: flake black mypy pytest

flake: venv
	$(VPYTHON) -m flake8 $(SRC)

black: venv
	$(VPYTHON) -m black $(SRC)

mypy: venv
	$(VPYTHON) -m mypy $(SRC)

pytest: venv testdata
	$(VPYTHON) -m pytest tests

venv: .venv/pyvenv.cfg

.venv/pyvenv.cfg: pyproject.toml
	$(PYTHON) -m venv .venv
	$(VPYTHON) -m pip install .[dev]
	$(VPYTHON) -m mypy --install-types --non-interactive
