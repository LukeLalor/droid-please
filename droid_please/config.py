import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from droid_please.prompts import (
    default_system_prompt,
    default_learn_prompt,
    default_summarize_prompt,
)
from pydantic import BaseModel

from droid_please.llm import AnthropicLLM


class Config(BaseModel):
    model: str = "claude-3-5-sonnet-latest"
    max_tokens: int = 8192
    pre_execution_hooks: list[str] = []
    post_execution_hooks: list[str] = []
    system_prompt: str = default_system_prompt
    learn_prompt: str = default_learn_prompt
    summarize_prompt: str = default_summarize_prompt
    project_root: str

    def get_system_prompt(self):
        summary_path = Path(self.project_root).joinpath(".droid").joinpath("summary.txt")
        try:
            project_summary = summary_path.read_text()
        except FileNotFoundError:
            project_summary = "Project summary has not yet been generated."
        return self.system_prompt.format(project_summary=project_summary)

    def llm(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                'ANTHROPIC_API_KEY must be set in .droid/.env or as an environment variable. Run "export ANTHROPIC_API_KEY=<your_key>" to set it.'
            )
        return AnthropicLLM(
            api_key=api_key,
            model=self.model,
            max_tokens=self.max_tokens,
        )

    def write(self, path: Path):
        with open(path, "w") as f:
            yaml.dump(self.model_dump(exclude={"project_root"}), f, sort_keys=False)


_config: Optional[Config] = None


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
    return config
