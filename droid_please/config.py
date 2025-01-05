import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


class Config(BaseModel):
    model: str = "claude-3-5-sonnet-latest"
    max_tokens: int = 8192
    project_root: str


_config: Config = None


def config() -> Config:
    if not _config:
        raise RuntimeError("Config not loaded")
    return _config


def _find_dot_droid() -> str:
    path = Path(os.getcwd())
    while not path.joinpath(".droid").exists():
        parent = path.parent
        if parent == path:
            raise FileNotFoundError("Could not find .droid directory")
        path = parent
    return path.resolve()


def load_config(config: Config = None):
    if not config:
        dot_droid = _find_dot_droid()
        config_file = Path(dot_droid).joinpath(".droid/config.yaml")
        c = None
        if config_file.exists():
            with open(config_file, "r") as f:
                c = yaml.safe_load(f)
        dotenv_loc = Path(dot_droid).joinpath(".droid/.env")
        if dotenv_loc.exists():
            load_dotenv(dotenv_loc)
        c = c or {}
        c["project_root"] = str(dot_droid)
        config = Config.model_validate(c)

    global _config
    _config = config
