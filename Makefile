# Variables
SERVER_IP := 172.16.15.41
DEPLOY_PATH := /pressplay_automator/
PYTHON := python3
PIP := pip3
VENV := venv
VENV_BIN := $(VENV)/bin

# Exclude patterns for deployment
EXCLUDE_PATTERNS := .venv/ .git/ __pycache__/ .pytest_cache/ logs/ .vscode/ *.pyc

.PHONY: help venv install deploy clean lint test run

# Default target when just running 'make'
help:
	@echo "Available commands:"
	@echo "  make venv         - Create virtual environment"
	@echo "  make install      - Install dependencies"
	@echo "  make deploy       - Deploy to server"
	@echo "  make clean        - Clean up generated files"
	@echo "  make lint         - Run code linting"
	@echo "  make test         - Run tests"
	@echo "  make run          - Run the application"

# Create virtual environment
venv:
	@echo "Creating virtual environment..."
	@$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created."

# Install dependencies
install:
	@echo "Installing dependencies..."
	@$(PIP) install -r requirements.txt
	@echo "Dependencies installed."

# Deploy to server
deploy:
	@echo "Deploying to $(SERVER_IP):$(DEPLOY_PATH)..."
	@rsync -av $(foreach pattern,$(EXCLUDE_PATTERNS),--exclude='$(pattern)') \
		--progress \
		* $(SERVER_IP):$(DEPLOY_PATH)
	@echo "Deployment complete!"

# Clean up generated files
clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*.pyd" -delete
	@find . -type f -name ".coverage" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@find . -type d -name "*.egg" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type d -name ".coverage" -exec rm -rf {} +
	@find . -type f -name ".DS_Store" -delete
	@echo "Clean up complete!"

# Run linting
lint:
	@echo "Running linting..."
	@$(VENV_BIN)/flake8 .
	@$(VENV_BIN)/black . --check
	@echo "Linting complete!"

# Run tests
test:
	@echo "Running tests..."
	@$(VENV_BIN)/pytest
	@echo "Tests complete!"

# Run the application
run:
	@echo "Starting application..."
	@$(PYTHON) main.py

# Run the application with specific arguments
run-with-args:
	@echo "Starting application with arguments..."
	@$(PYTHON) main.py $(filter-out $@,$(MAKECMDGOALS))

# Allow passing arguments to run-with-args
%:
	@: 