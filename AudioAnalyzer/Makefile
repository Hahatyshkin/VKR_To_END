# AudioAnalyzer Makefile
# Run commands: make <target>

.PHONY: help install install-dev test test-cov lint format check clean build run

# Default target
help:
	@echo "AudioAnalyzer Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup:"
	@echo "  install       Install production dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test          Run all tests"
	@echo "  test-cov      Run tests with coverage report"
	@echo "  test-ui       Run UI tests (requires display)"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint          Run all linters (mypy, pylint)"
	@echo "  format        Format code with black and isort"
	@echo "  check         Run format check without modifying files"
	@echo ""
	@echo "Build:"
	@echo "  build         Build executable with PyInstaller"
	@echo "  clean         Clean build artifacts"
	@echo ""
	@echo "Run:"
	@echo "  run           Run the application"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install 2>/dev/null || true

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

test-ui:
	pytest tests/ -v -m ui

test-integration:
	pytest tests/ -v -m integration

test-quick:
	pytest tests/ -v -m "not slow"

# Code Quality
lint:
	@echo "Running mypy..."
	mypy src/ --ignore-missing-imports
	@echo "Running pylint..."
	pylint src/ --exit-zero

lint-strict:
	mypy src/ --strict
	pylint src/

format:
	black src/ tests/
	isort src/ tests/

format-check:
	black --check src/ tests/
	isort --check-only src/ tests/

check: format-check lint

# Build
build:
	pyinstaller src/app.py --name AudioAnalyzer --windowed --onefile

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .coverage htmlcov coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run
run:
	python -m src.app

# CI targets
ci: install-dev check test-cov

pre-commit:
	pre-commit run --all-files
