# Tamil–English Benchmark (TEB) — developer tasks.
# Works on Linux/macOS (make) and on Windows via `make` in Git Bash/WSL,
# or by copying the underlying commands.

PYTHON ?= python
PORT_API ?= 8000
PORT_UI ?= 8501

.PHONY: help install install-dev fmt lint type test test-unit test-integration test-e2e \
        dataset bench report ui api doctor clean

help:
	@echo "Targets:"
	@echo "  install        pip install -e ."
	@echo "  install-dev    pip install -e '.[dev]'"
	@echo "  fmt            ruff format + fix"
	@echo "  lint           ruff check"
	@echo "  type           mypy app"
	@echo "  test           full pytest suite"
	@echo "  dataset        build + validate + import the dataset"
	@echo "  bench          run the offline mock benchmark"
	@echo "  report         generate markdown/html/json/csv reports for job 1"
	@echo "  ui             streamlit dashboard"
	@echo "  api            uvicorn API"
	@echo "  doctor         environment diagnostics"
	@echo "  clean          remove caches and generated data"

install:
	$(PYTHON) -m pip install -e .

install-dev:
	$(PYTHON) -m pip install -e ".[dev]"

fmt:
	ruff format app scripts tests
	ruff check --fix app scripts tests

lint:
	ruff check app scripts tests
	ruff format --check app scripts tests

type:
	mypy app

test:
	$(PYTHON) -m pytest -q

test-unit:
	$(PYTHON) -m pytest tests/unit -q

test-integration:
	$(PYTHON) -m pytest tests/integration -q

test-e2e:
	$(PYTHON) -m pytest tests/e2e -q

dataset:
	$(PYTHON) -m app.cli.main dataset build
	$(PYTHON) -m app.cli.main dataset validate benchmark/data/v1.0.0/examples.jsonl
	$(PYTHON) -m app.cli.main dataset import benchmark/data/v1.0.0/examples.jsonl

bench:
	$(PYTHON) -m app.cli.main eval run --provider mock --name offline-demo

report:
	$(PYTHON) -m app.cli.main eval report --job 1 --format markdown --out reports/demo_report.markdown
	$(PYTHON) -m app.cli.main eval report --job 1 --format html --out reports/demo_report.html
	$(PYTHON) -m app.cli.main eval report --job 1 --format json --out reports/demo_report.json
	$(PYTHON) -m app.cli.main eval report --job 1 --format csv --out reports/demo_results.csv

ui:
	$(PYTHON) -m streamlit run app/ui/app.py --server.port $(PORT_UI)

api:
	$(PYTHON) -m uvicorn app.api.main:app --port $(PORT_API) --host 127.0.0.1

doctor:
	$(PYTHON) -m app.cli.main doctor

clean:
	$(PYTHON) -c "import shutil,glob,os; [shutil.rmtree(p,ignore_errors=True) for p in glob.glob('**/__pycache__',recursive=True)]"
	$(PYTHON) -c "import shutil; [shutil.rmtree(p,ignore_errors=True) for p in ('.pytest_cache','.mypy_cache','.ruff_cache','htmlcov')]"
