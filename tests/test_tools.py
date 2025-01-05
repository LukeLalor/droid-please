from pathlib import Path

import pytest

from droid_please.config import load_config, Config
from droid_please.tools import (
    create_file,
    read_file,
    update_file,
    rename_file,
    delete_file,
    ls, Update,
)


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


def test_update_file(config):
    create_file("foo.txt", ["line1", "line2", "line3"])
    update_file(
        "foo.txt",
        [Update.model_validate({"insert_line": 2, "replace_until_line": 3, "content": ["new line2"]})],
    )
    with open(Path(config.project_root).joinpath("foo.txt"), "r") as f:
        assert f.read() == "line1\nnew line2\nline3"


def test_rename_file(config):
    create_file("old.txt", ["content"])
    rename_file("old.txt", "new.txt")
    assert not Path(config.project_root).joinpath("old.txt").exists()
    with open(Path(config.project_root).joinpath("new.txt"), "r") as f:
        assert f.read() == "content"


def test_delete_file(config):
    create_file("to_delete.txt", ["content"])
    delete_file("to_delete.txt")
    assert not Path(config.project_root).joinpath("to_delete.txt").exists()


def test_ls(config):
    create_file("file1.txt", ["content1"])
    create_file("file2.txt", ["content2"])
    files = ls("")
    assert "file1.txt" in files
    assert "file2.txt" in files
