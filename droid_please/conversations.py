import glob
from pathlib import Path

from droid_please.config import config


def latest_loc_path() -> Path:
    return Path(config().project_root).joinpath(".droid/conversations/latest.yaml")


def next_conversation_number() -> Path:
    conv_dir = Path(config().project_root).joinpath(".droid/conversations")
    existing_files = glob.glob(str(conv_dir.joinpath("*.yaml")))
    if not existing_files:
        return conv_dir.joinpath("0001.yaml")
    numbers = [int(name) for name in (Path(f).stem for f in existing_files) if name.isdigit()]
    return conv_dir.joinpath(f"{max(numbers) + 1:04d}.yaml")
