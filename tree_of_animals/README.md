# Tree of Animals

A Python project for working with hierarchical animal classifications.

## Setup

### Python Virtual Environment

This project uses a Python virtual environment located in the `.venv` directory.

### Quick Start

To activate the virtual environment, run:

```bash
source activate.sh
```

Or manually activate it:

```bash
source .venv/bin/activate
```

### Deactivation

To deactivate the virtual environment:

```bash
deactivate
```

## Requirements

- Python 3.x

## Project Structure

```
tree_of_animals/
├── .venv/              # Python virtual environment
├── activate.sh         # Convenience script to activate the environment
└── README.md          # This file
```

## Development

After activating the virtual environment, you can install dependencies:

```bash
pip install <package-name>
```

To save your dependencies:

```bash
pip freeze > requirements.txt
```

To install from requirements.txt:

```bash
pip install -r requirements.txt
```
