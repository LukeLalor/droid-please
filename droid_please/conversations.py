import glob
from pathlib import Path

from droid_please.config import config


def latest_loc_path() -> Path:
    return Path(config().project_root).joinpath(".droid/conversations/latest.yaml")


def next_conversation_number() -> Path:
    conv_dir = Path(config().project_root).joinpath(".droid/conversations")
    existing_files = glob.glob(str(conv_dir.joinpath("*.yaml")))
    numbers = [int(name) for name in (Path(f).stem for f in existing_files) if name.isdigit()]
    return conv_dir.joinpath(f"{max(numbers, default=0) + 1:03d}.yaml")
