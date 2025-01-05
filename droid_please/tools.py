from pathlib import Path
from typing import Tuple, List

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
        lines = f.readlines()
        number_length = len(str(min(len(lines), limit - 1)))
        rtn = "\n".join(
            (
                f"{i}.{' '*(number_length-len(str(i)))}|{lines[i-1]}"
                for i in range(1, min(len(lines), limit))
            )
        )
        if len(lines) > limit:
            rtn += f"\n...{len(lines)-limit} lines not shown"
        return rtn


def create_file(file_path: str, contents: str):
    """
    Create a file with the given contents.
    """
    _check_file_path(file_path)
    loc = Path(config().project_root).joinpath(file_path)
    with open(loc, "w") as f:
        f.write(contents)


class Update(BaseModel):
    replace_lines: Tuple[int, int]
    content: str


def update_file(file_path: str, updates: List[Update]):
    """
    Update a file with the given updates. Each update is a tuple of the line number to replace and the new content.
    The second element of the tuple is exclusive, so to purely insert content, use the same line number for both.
    If multiple updates are give, lines numbers always refer to the original file before any updates are applied.
    Examples:
        {"replace_lines": (1, 4), "content": "new content"} will replace lines 1, 2, and 3 with "new content".
        {"replace_lines": (1, 1), "content": "new content"} will insert "new content" at line 1. Existing content will all be pushed down a line
    """
    _check_file_path(file_path)
    loc = Path(config().project_root).joinpath(file_path)
    with open(loc, "r") as f:
        lines = f.readlines()
    lines_to_delete = set()
    insertion_points = dict()
    for update in updates:
        for i in range(*update.replace_lines):
            lines_to_delete.add(i)
        insertion_points[update.replace_lines[0]] = update.content
    acc = []
    for i in range(len(lines)):
        if i in insertion_points:
            acc.append(insertion_points[i])
        if i not in lines_to_delete:
            acc.append(lines[i])
    with open(loc, "w") as f:
        f.write("\n".join(acc))
    return read_file(file_path)
