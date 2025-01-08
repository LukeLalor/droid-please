import pytest
import tempfile
import os
from pathlib import Path

from click.testing import Result
from dotenv import load_dotenv
from typer.testing import CliRunner
from droid_please.main import app

load_dotenv()
runner = CliRunner()


@pytest.fixture(scope='module')
def vcr(vcr):
    vcr.match_on = ['method', 'host', 'port', 'path', 'query', 'body']
    vcr.filter_headers = ['x-api-key']
    return vcr


@pytest.fixture(scope="module")
def tmp_project():
    """Create a temporary directory for project testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        yield Path(tmpdir)
        os.chdir(original_dir)


# tests need to run in order to save llm / debugging costs for now. todo, consider mocking llm
@pytest.mark.vcr()
def test_init_command(tmp_project):
    """Test project initialization command."""
    result = runner.invoke(app, ["init", str(tmp_project)])
    _check_exit_code(result)
    assert (tmp_project / ".droid").exists()


@pytest.mark.vcr()
def test_please(tmp_project):
    """Test creating a small chess guide project using natural language commands."""
    # Initialize the project first
    # Create project structure using natural language
    command: str = (
        "create a README.md with a chess guide introduction create an basics/openings.md file explaining "
        "basic chess openings. Limit both files to a 20 word in total. We will write the rest of the files later."
    )

    result = runner.invoke(app, ["please", command])
    _check_exit_code(result)

    # Verify created files and directories
    assert (tmp_project / "README.md").exists()
    assert (tmp_project / "basics").is_dir()
    assert (tmp_project / "basics" / "openings.md").exists()


@pytest.mark.vcr()
def test_continue(tmp_project):
    """Test updating existing files using natural language commands."""
    # Create initial file
    result = runner.invoke(app, ["continue", "Add the Ruy Lopez to the openings file"])
    _check_exit_code(result)

    # Verify content was updated
    with open(tmp_project / "basics" / "openings.md") as f:
        content = f.read()
        assert "ruy lopez" in content.lower()


@pytest.mark.vcr()
def test_learn(tmp_project):
    """Test listing project files using natural language commands."""
    # Create some files first
    runner.invoke(app, ["learn"])
    result = runner.invoke(app, ["please", "tell me about this project"])
    assert "chess" in result.stdout.lower()


@pytest.mark.vcr()
def test_rename_file(tmp_project):
    """Test renaming files using natural language commands."""
    # Create a file first
    result = runner.invoke(app, ["please", "rename openings.md to old_openings.md"])
    _check_exit_code(result)
    assert (tmp_project / "basics" / "old_openings.md").exists()


@pytest.mark.vcr()
def test_delete_file(tmp_project):
    """Test deleting files using natural language commands."""
    # Create a file first
    result = runner.invoke(app, ["continue", "delete old_openings.md"])
    _check_exit_code(result)
    assert not (tmp_project / "basics" / "old_openings.md").exists()


def _check_exit_code(result: Result):
    assert result.exit_code == 0, dict(stdout=result.stdout, stderr=result.stderr)
