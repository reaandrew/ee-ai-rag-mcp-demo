.PHONY: clean test lint coverage install build-lambda sonar-scan

# Python paths
PYTHON = python3
PIP = pip3
PYTEST = pytest
PYLINT = pylint
BLACK = black
FLAKE8 = flake8

# Directories
SRC_DIR = src
TESTS_DIR = tests
BUILD_DIR = build
COVERAGE_DIR = coverage-reports

# Install dependencies
install:
	$(PIP) install -e .
	$(PIP) install -r requirements-dev.txt

# Run tests
test:
	$(PYTEST)

# Run tests with coverage
coverage:
	$(PYTEST) --cov=$(SRC_DIR) --cov-report=xml:$(COVERAGE_DIR)/python-coverage.xml --cov-report=term

# Lint the code
lint:
	$(FLAKE8) $(SRC_DIR)
	$(BLACK) --check $(SRC_DIR) $(TESTS_DIR)

# Format the code
format:
	$(BLACK) $(SRC_DIR) $(TESTS_DIR)

# Build Lambda function packages
build-lambda:
	mkdir -p $(BUILD_DIR)
	./build_lambda.sh

# Run SonarQube scan
sonar-scan:
	npm run sonar

# Clean up
clean:
	rm -rf $(BUILD_DIR)
	rm -rf $(COVERAGE_DIR)
	rm -rf *.egg-info
	rm -rf __pycache__
	rm -rf .pytest_cache
	find . -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete