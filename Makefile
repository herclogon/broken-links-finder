# Makefile for Broken Link Checker Tests
# Provides convenient commands for testing and development

.PHONY: help install test test-unit test-integration test-cli test-quick lint clean coverage setup all

# Default target
help:
	@echo "Broken Link Checker - Test Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  make setup          - Install all dependencies (main + test)"
	@echo "  make install        - Install test dependencies only"
	@echo ""
	@echo "Test Commands:"
	@echo "  make test           - Run all tests with coverage (default)"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-cli       - Run CLI tests only"
	@echo "  make test-quick     - Run tests without coverage (faster)"
	@echo ""
	@echo "Quality Commands:"
	@echo "  make lint           - Run code linting"
	@echo "  make coverage       - Generate coverage report"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make clean          - Clean up test artifacts"
	@echo "  make all            - Run setup, lint, and all tests"
	@echo ""
	@echo "Examples:"
	@echo "  make setup && make test"
	@echo "  make test-unit"
	@echo "  make lint"

# Install all dependencies
setup:
	@echo "Installing main dependencies..."
	pip install -r requirements.txt
	@echo "Installing test dependencies..."
	pip install -r test_requirements.txt
	@echo "✅ All dependencies installed"

# Install test dependencies only
install:
	@echo "Installing test dependencies..."
	pip install -r test_requirements.txt
	@echo "✅ Test dependencies installed"

# Run all tests with coverage (default)
test:
	@echo "Running all tests with coverage..."
	python run_tests.py --all

# Run unit tests only
test-unit:
	@echo "Running unit tests..."
	python run_tests.py --unit

# Run integration tests only
test-integration:
	@echo "Running integration tests..."
	python run_tests.py --integration

# Run CLI tests only
test-cli:
	@echo "Running CLI tests..."
	python run_tests.py --cli

# Run quick tests without coverage
test-quick:
	@echo "Running quick tests..."
	python run_tests.py --quick

# Run code linting
lint:
	@echo "Running code linting..."
	python run_tests.py --lint

# Generate coverage report
coverage: test
	@echo "Coverage report generated in htmlcov/index.html"
	@if command -v xdg-open > /dev/null; then \
		echo "Opening coverage report..."; \
		xdg-open htmlcov/index.html; \
	elif command -v open > /dev/null; then \
		echo "Opening coverage report..."; \
		open htmlcov/index.html; \
	else \
		echo "Open htmlcov/index.html in your browser to view the coverage report"; \
	fi

# Clean up test artifacts
clean:
	@echo "Cleaning up test artifacts..."
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf *.pyc
	rm -rf test_*.json
	rm -rf broken_links_report_*.json
	rm -rf crawler_state_*.json
	@echo "✅ Cleanup complete"

# Run everything: setup, lint, and all tests
all: setup lint test
	@echo "🎉 All operations completed successfully!"

# Development workflow
dev: install test-quick
	@echo "🚀 Development workflow complete"

# Continuous integration workflow
ci: install lint test
	@echo "🔄 CI workflow complete"
