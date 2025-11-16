.PHONY: help install test test-unit test-integration test-security coverage clean lint format

help:
	@echo "Available commands:"
	@echo "  make install          - Install dependencies"
	@echo "  make test             - Run all tests"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-security    - Run security tests only"
	@echo "  make coverage         - Run tests with coverage report"
	@echo "  make lint             - Run code linting"
	@echo "  make format           - Format code with black"
	@echo "  make clean            - Remove test artifacts"

install:
	pip install -r requirements-dev.txt --use-deprecated=legacy-resolver

test:
	pytest tests/ -v

test-unit:
	pytest tests/test_user.py::TestUserModel tests/test_item.py::TestItemModel -v

test-integration:
	pytest tests/test_api_integration.py -v

test-security:
	pytest tests/test_security.py -v

coverage:
	pytest tests/ --cov=code --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf *.db
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

lint:
	flake8 code/ tests/ || true

format:
	black code/ tests/

run:
	cd code && python app.py

init-db:
	cd code && python create_tables.py
