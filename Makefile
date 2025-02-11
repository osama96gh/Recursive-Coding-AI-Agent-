.PHONY: init clean run test upgrade-pip

# Variables
VENV_PYTHON := venv/bin/python3
VENV_PIP := venv/bin/pip
VENV_ACTIVATE := . venv/bin/activate

# Create virtual environment and install dependencies
init:
	python3 -m venv venv
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt
	$(VENV_PIP) install -e .

# Upgrade pip to latest version
upgrade-pip:
	$(VENV_PIP) install --upgrade pip

# Run the project
run:
	$(VENV_PYTHON) src/main.py

# Run tests
test:
	$(VENV_PYTHON) -m pytest tests/

# Clean up generated files and virtual environment
clean:
	rm -rf venv
	rm -rf logs/*
	rm -rf __pycache__
	rm -rf src/__pycache__
	rm -rf src/*/__pycache__
	rm -rf src/*/*/__pycache__
	rm -rf tests/__pycache__
	rm -rf *.egg-info
