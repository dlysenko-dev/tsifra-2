# Digital Clone v3 — Makefile
# ============================

.PHONY: install run test lint format clean docker

PYTHON := python3
PIP := pip3

install:
	$(PIP) install -r requirements.txt
	playwright install chromium

run:
	$(PYTHON) main.py

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=. --cov-report=html

lint:
	ruff check .
	bandit -r core/ agents/ skills/ memory/

format:
	black core/ agents/ skills/ memory/ tests/ main.py
	ruff check --fix .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache/ .coverage htmlcov/

docker:
	docker-compose up --build

docker-down:
	docker-compose down

# Security check
security:
	bandit -r core/ agents/ skills/ memory/ -f json -o bandit-report.json
	@echo "Security report: bandit-report.json"
