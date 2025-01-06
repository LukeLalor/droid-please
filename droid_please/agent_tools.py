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
            rtn = f"({offset} leading lines skipped)\n" + rtn
        if len(lines) > limit:
            rtn += f"\n({len(lines) - limit} trailing lines not shown)"
        return rtn


def create_file(file_path: str, lines: List[str], trailing_newline: bool = True):
    """
    Create a file with the given contents.
    """
    _check_file_path(file_path)
    loc = Path(config().project_root).joinpath(file_path)
    if loc.exists():
        raise FileExistsError(
            f"File already exists. Update it instead or explicitly delete it first."
        )
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


def update_file(
    file_path: str,
    insertions: List[InsertLines] = None,
    deletions: List[DeleteLines] = None,
):
    """
    Update a file with the given updates. Each update contains either lines to insert or a range of lines to delete.
    Inserting will insert before the specified line. For example, start_line=0 will insert at the beginning of the file. start_line=4 will insert before line 4, after line 3. This will not delete any lines, including the specified insertion index.
    Deleting will delete all lines from start_line to end_line, inclusive. This will only delete lines as they existed BEFORE any insertions.
    """
    insertions = insertions or []
    deletions = deletions or []
    if not insertions and not deletions:
        raise ValueError("No updates provided")
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
    potential_min_lines = []
    potential_max_lines = []
    if insertion_lines:
        potential_min_lines.append(min(insertion_lines.keys()))
        potential_max_lines.append(max((1 + i + len(lines) for i in insertion_lines.keys())))
    if deletions:
        potential_min_lines.append(min(deletions, key=lambda d: d.start_line).start_line)
        potential_max_lines.append(max(deletions, key=lambda d: d.end_line).end_line)
    offset = max(min(potential_min_lines) - 5, 0)
    limit = min((max(potential_max_lines) + 5), len(lines)) - offset
    return (
        "Here is the updated portion of the file. If this does not look right please update it again.\n"
        + _read_file(loc, offset, limit)
    )


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
