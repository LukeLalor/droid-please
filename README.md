# Droid Please

A simple CLI tool that acts as your AI coding assistant, powered by Anthropic's Claude. It helps you manage your project through natural language commands, allowing you to perform various file operations and coding tasks by simply asking.

## Features

- Natural language interface for project management
- File operations (read, update, rename, delete)
- Directory listing
- Interactive CLI experience
- Powered by Anthropic's Claude AI model

## Installation

This project uses Poetry for dependency management. To install:

```bash
pip install droid-please
```

## Configuration

1. Set up your Anthropic API key as an environment variable:
```bash
export ANTHROPIC_API_KEY=your-api-key
```

## Usage

After installation, you can use the CLI tool with the `droid` command:

```bash
# Start an interactive session
droid please

# Or directly pass a command
droid please "update the version number in pyproject.toml"
```

The assistant will interpret your natural language commands and perform the appropriate actions on your project files.

## Requirements

- Python 3.10 or higher
- Poetry for dependency management
- Anthropic API key

## Dependencies

- anthropic: Anthropic API client
- typer: CLI interface
- rich: Terminal formatting
- pydantic: Data validation
- python-dotenv: Environment variable management
- pyyaml: YAML file handling
- jsonschema: JSON schema validation

## Development

To contribute to the development:

```bash
# Install development dependencies
poetry install --with dev

# Run tests
poetry run pytest

# Run linter
poetry run ruff check .
```

## License

[License information needed]

## Author

Luke Lalor (lukehlalor@gmail.com)