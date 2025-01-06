from collections import defaultdict
from pathlib import Path
from typing import List
import shutil

from anthropic import BaseModel
from droid_please.config import config


def _check_file_path(file_path: str):
    root = Path(config().project_root)
    loc = root.joinpath(file_path)
    if not loc.is_relative_to(root):
        raise ValueError("Cannot interact with files outside of project root")


def read_file(file_path: str, offset: int = 0) -> str:
    """
    Read a file and return its contents. Prepends each line with the line number. Example: "1 |line1 content"
    """
    _check_file_path(file_path)
    loc = Path(config().project_root).joinpath(file_path)
    if not loc.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return _read_file(loc, offset, 100)


def _read_file(loc, offset, limit):
    limit = limit + offset
    with open(loc, "r") as f:
        content = f.read()
        lines = content.splitlines()
        if content.endswith("\n"):
            lines.append("")
        number_length = len(str(min(len(lines), limit - 1)))
        rtn = "\n".join(
            (
                f"{i}{' ' * (number_length - len(str(i)))}|{lines[i - 1]}"
                for i in range(1 + offset, min(len(lines) + 1, limit))
            )
        )
        if offset > 0:
            rtn = f"\n({offset} leading lines skipped)\n" + rtn
        if len(lines) > limit:
            rtn += f"\n({len(lines) - limit} trailing lines not shown)\n"
        return rtn


def create_file(file_path: str, lines: List[str], trailing_newline: bool = True):
    """
    Create a file with the given contents.
    """
    _check_file_path(file_path)
    loc = Path(config().project_root).joinpath(file_path)
    loc.parent.mkdir(parents=True, exist_ok=True)
    if trailing_newline and (not lines or lines[-1] != ""):
        lines.append("")
    with open(loc, "w") as f:
        f.write("\n".join(lines))


class InsertLines(BaseModel):
    insertion_index: int
    lines: List[str]


class DeleteLines(BaseModel):
    start_line: int
    end_line: int


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


def update_file(file_path: str, insertions: List[InsertLines] = None, deletions: List[DeleteLines] = None):
    """
    Update a file with the given updates. Each update contains either lines to insert or a range of lines to delete.
    Inserting will insert at the index of the specified line. For example, start_line=0 will insert at the beginning of the file. start_line=4 will insert before line 4, after line 3.
    Deleting will delete all lines from start_line to end_line, inclusive. This will only delete lines as they existed BEFORE any insertions.
    """
    insertions = insertions or []
    deletions = deletions or []
    _check_file_path(file_path)
    loc = Path(config().project_root).joinpath(file_path)
    with open(loc, "r") as f:
        content = f.read()
        lines = content.splitlines()
    if content.endswith("\n"):
        lines.append("")
    lines_to_delete = set()
    for deletion in deletions:
        for i in range(deletion.start_line, deletion.end_line + 1):
            lines_to_delete.add(i)
    insertion_lines = defaultdict(list)
    for update in insertions:
        insertion_lines[update.insertion_index].extend(update.lines)
    acc = []
    for i in range(len(lines)):
        if i in insertion_lines:
            acc.extend(insertion_lines[i])
        if i + 1 not in lines_to_delete:
            acc.append(lines[i])
    with open(loc, "w") as f:
        f.write("\n".join(acc))
    min_line_effected = min(insertion_lines.keys())
    if deletions:
        min_line_effected = min(min_line_effected, min(deletions, key=lambda d: d.start_line).start_line)
    max_line_effected = max((i.insertion_index + len(i.lines) for i in insertions))
    if deletions:
        max_line_effected = max(max_line_effected, max(deletions, key=lambda d: d.end_line).end_line)
    offset = max(min_line_effected-5, 0)
    limit = min((max_line_effected + 5) - min_line_effected, len(lines)-offset)
    return _read_file(loc, offset, limit)


def delete_path(path: str):
    """
    Delete a file or directory.
    """
    _check_file_path(path)
    loc = Path(config().project_root).joinpath(path)
    if loc.is_dir():
        shutil.rmtree(loc)
        return f"Deleted directory {path}"
    else:
        loc.unlink()
        return f"Deleted file {path}"


def ls(path: str = "."):
    """
    List contents of a directory.
    """
    _check_file_path(path)
    loc = Path(config().project_root).joinpath(path)
    if not loc.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    return [dict(name=p.name, is_dir=p.is_dir()) for p in loc.iterdir()]
