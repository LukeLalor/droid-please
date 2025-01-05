from pathlib import Path

import pytest

from droid_please.config import load_config, Config
from droid_please.tools import create_file, read_file


@pytest.fixture(autouse=True)
def config(tmp_path):
    project_root = tmp_path.joinpath("test_project_root")
    project_root.mkdir()
    return load_config(Config(project_root=str(project_root)))


def test_create_file(config):
    create_file("foo.txt", ["line1", "line2", ""])
    with open(Path(config.project_root).joinpath("foo.txt"), "r") as f:
        assert f.read() == "line1\nline2\n"


def test_read_file(config):
    create_file("foo.txt", ["line1", "line2", ""])
    assert read_file("foo.txt") == "1|line1\n2|line2\n3|"
