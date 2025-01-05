from pathlib import Path
from typing import List

from anthropic import BaseModel
from droid_please.config import config


def _check_file_path(file_path: str):
    root = Path(config().project_root)
    loc = root.joinpath(file_path)
    if not loc.is_relative_to(root):
        raise ValueError("Cannot interact with files outside of project root")


def read_file(file_path: str) -> str:
    """
    Read a file and return its contents. Prepends each line with the line number. Example: "1. |line1 content"
    """
    _check_file_path(file_path)
    loc = Path(config().project_root).joinpath(file_path)
    if not loc.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(loc, "r") as f:
        limit = 10000
        content = f.read()
        lines = content.splitlines()
        if content.endswith("\n"):
            lines.append("")
        number_length = len(str(min(len(lines), limit - 1)))
        rtn = "\n".join(
            (
                f"{i}{' '*(number_length-len(str(i)))}|{lines[i-1]}"
                for i in range(1, min(len(lines) + 1, limit))
            )
        )
        if len(lines) > limit:
            rtn += f"\n...{len(lines)-limit} lines not shown"
        return rtn


def create_file(file_path: str, lines: List[str]):
    """
    Create a file with the given contents.
    """
    _check_file_path(file_path)
    loc = Path(config().project_root).joinpath(file_path)
    with open(loc, "w") as f:
        f.write("\n".join(lines))


class Update(BaseModel):
    insert_line: int
    replace_until_line: int
    content: List[str]


def rename_file(old_path: str, new_path: str):
    """
    Rename a file.
    """
    _check_file_path(old_path)
    _check_file_path(new_path)
    old_loc = Path(config().project_root).joinpath(old_path)
    new_loc = Path(config().project_root).joinpath(new_path)
    old_loc.rename(new_loc)
    return f"Renamed {old_path} to {new_path}"


def update_file(file_path: str, updates: List[Update]):
    """
    Update a file with the given updates. Each update is a tuple of the line number to replace and the new content.
    The second element of the tuple is exclusive, so to purely insert content, use the same line number for both.
    If multiple updates are give, lines numbers always refer to the original file before any updates are applied.
    Examples:
        {"file_path": "foo.txt", "updates": [{"insert_line": 1, "replace_until_line": 4, "content": ["new content"]}]} will replace lines 1, 2, and 3 with "new content".
        {"file_path": "foo.txt", "updates": [{"insert_line": 1, "replace_until_line": 1, "content": ["new content"]}]} will insert "new content" at line 1. Existing content will all be pushed down a line but otherwise remain unchanged.
    """
    _check_file_path(file_path)
    loc = Path(config().project_root).joinpath(file_path)
    with open(loc, "r") as f:
        lines = f.read().splitlines()
    lines_to_delete = set()
    insertion_lines = dict()
    for update in updates:
        for i in range(update.insert_line, update.replace_until_line):
            lines_to_delete.add(i)
        insertion_lines[update.insert_line] = update.content
    acc = []
    for i in range(len(lines)):
        line_number = i+1
        if line_number in insertion_lines:
            acc.extend(insertion_lines[line_number])
        if line_number not in lines_to_delete:
            acc.append(lines[i])
    with open(loc, "w") as f:
        f.write("\n".join(acc))
    return read_file(file_path)


def delete_file(file_path: str):
    """
    Delete a file.
    """
    _check_file_path(file_path)
    loc = Path(config().project_root).joinpath(file_path)
    loc.unlink()
    return f"Deleted {file_path}"


def ls(path: str = ""):
    """
    List contents of a directory.
    """
    _check_file_path(path)
    loc = Path(config().project_root).joinpath(path)
    if not loc.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    return [dict(name=p.name, is_dir=p.is_dir()) for p in loc.iterdir()]
