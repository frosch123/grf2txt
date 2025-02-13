.PHONY: all test flake black mypy pytest venv testdata

PYTHON=python3
VPYTHON=.venv/bin/python3
NMLC=.venv/bin/nmlc
SRC=grf2txt tests

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

testdata: tests/test_data/test.grf

%.grf: %.nml
	$(NMLC) --grf $@ -l $(<D)/lang $<
