# Droid Please

A simple CLI tool that acts as your AI coding assistant, powered by Anthropic's Claude. It helps you manage your project through natural language commands, allowing you to perform various file operations and coding tasks by simply asking.

## Quick Start

```bash
# Install the package
pip install droid-please

# Set your API key
export ANTHROPIC_API_KEY=your-api-key

# Start using it!
droid please  # interactive mode
droid please "update the version in pyproject.toml"  # direct command
```

## Features

- 💬 Natural language interface for project management
- 📁 File operations:
  - Read file contents
  - Create new files
  - Update existing files
  - Rename files
  - Delete files
  - List directory contents
- 🤖 Powered by Anthropic's Claude AI model
- 💻 Interactive CLI experience
- 🔄 Context-aware file operations

## Installation

### Using pip
```bash
pip install droid-please
```

### From source
```bash
git clone https://github.com/yourusername/droid-please.git
cd droid-please
poetry install
```

## Configuration

1. Get an API key from [Anthropic](https://www.anthropic.com/)
2. Set up your Anthropic API key as an environment variable:
```bash
export ANTHROPIC_API_KEY=your-api-key
```

You can also add this to your `.bashrc`, `.zshrc`, or equivalent to make it permanent.

## Usage

### Interactive Mode
```bash
droid please
```
This starts an interactive session where you can type commands in natural language.

### Direct Commands
```bash
droid please "read the contents of config.py"
droid please "update the version number to 1.0.0 in pyproject.toml"
droid please "create a new file called example.txt with Hello World content"
```

### Example Commands
- `"Show me what's in the src directory"`
- `"Create a new Python file called utils.py"`
- `"Update the project description in pyproject.toml"`
- `"Delete the temporary files in the cache directory"`
- `"Rename old_file.txt to new_file.txt"`

## Requirements

- Python 3.10 or higher
- Anthropic API key

## Development

This project uses Poetry for dependency management and development workflows.

### Setting up the development environment

```bash
# Clone the repository
git clone https://github.com/yourusername/droid-please.git
cd droid-please

# Install all dependencies including development ones
poetry install --with dev

# Activate the virtual environment
poetry shell
```

### Running Tests
```bash
poetry run pytest
```

### Code Quality
```bash
# Run linter
poetry run ruff check .
```

## Dependencies

- `anthropic`: Anthropic API client for Claude integration
- `typer`: Modern CLI framework for Python
- `rich`: Rich text and beautiful formatting in the terminal
- `pydantic`: Data validation using Python type annotations
- `python-dotenv`: Environment variable management
- `pyyaml`: YAML file handling
- `jsonschema`: JSON schema validation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

[Add your license information here]

