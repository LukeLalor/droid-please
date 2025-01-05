import os
import readline
import time
from pathlib import Path
from typing import Annotated, Optional

import typer
from anthropic import AuthenticationError
from anthropic.types import MessageParam
from rich.console import Console
from rich.style import Style

from droid_please.agent import Agent
from droid_please.agent_tools import read_file, update_file, rename_file, delete_path, ls, create_file
from droid_please.config import load_config, config, Config
from droid_please.llm import ResponseChunk, ToolCallChunk, ToolResponse

assert readline  # importing this allows better cli experience, assertion to prevent optimize imports from removing it

app = typer.Typer()

console = Console()
agent_console = Console(style="green italic")
dim_console = Console(style=Style(dim=True))
err_console = Console(stderr=True, style="red")


@app.callback()
def callback():
    """
    Droid, your coding ai assistant
    """
    pass


@app.command()
def init(loc: Annotated[Path, typer.Argument()] = Path.cwd()):
    """
    Initialize a new .droid directory in the current directory with required configuration files.
    """
    droid_dir = loc.joinpath(".droid")
    try:
        droid_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        err_console.print(f"Directory {droid_dir} already exists")
        raise SystemExit(1)
    
    # Create an empty config.yaml
    config_yaml = droid_dir.joinpath("config.yaml")
    Config(project_root=str(loc)).write(config_yaml)
    load_config()

    # Create a default .gitignore file if it doesn't exist
    gitignore_path = droid_dir.joinpath(".gitignore")
    with open(gitignore_path, "w") as f:
        f.write(".env\nconversation.yaml\n")

    if not os.getenv("ANTHROPIC_API_KEY"):
        # prompt for the api key. not required but recommended
        api_key = typer.prompt("Anthropic API key (optional)", default="", show_default=False)
        if api_key:
            with open(droid_dir.joinpath(".env"), "w") as f:
                f.write(f"ANTHROPIC_API_KEY={api_key}")


def _load_config():
    try:
        load_config()
    except FileNotFoundError:
        err_console.print("Could not find .droid directory. Run \"droid init\" to create one.")
        raise SystemExit(1)


def _llm():
    try:
        return config().llm()
    except RuntimeError as e:
        err_console.print(str(e))
        raise SystemExit(1)


@app.command()
def please(command: Annotated[Optional[str], typer.Argument()] = None):
    """
    Ask the droid to do something.
    """
    _load_config()
    agent = Agent(llm=_llm())
    while True:
        command = command or typer.prompt(text=">", prompt_suffix="")
        execution_loop(agent, command)
        command = None


@app.command(name="continue")
def continue_(command: Annotated[Optional[str], typer.Argument()] = None):
    """
    Continue a conversation with the droid.
    """
    _load_config()
    agent = Agent.load(
        Path(config().project_root).joinpath(".droid/conversation.yaml"),
        llm=_llm(),
    )
    while True:
        command = command or typer.prompt(text=">", prompt_suffix="")
        execution_loop(agent, command)
        command = None


def execution_loop(agent: Agent, command: str):
    status = console.status("thinking...")
    status.start()
    last_chunk = None
    t0 = time.perf_counter()
    try:
        for chunk in agent.stream(
            messages=[MessageParam(content=command, role="user")],
            tools=[read_file, create_file, update_file, rename_file, delete_path, ls],
        ):
            if isinstance(chunk, ResponseChunk):
                if status:
                    status.stop()
                    status = None
                if not last_chunk or isinstance(last_chunk, ResponseChunk):
                    agent_console.print(chunk.content, end="")
                else:
                    agent_console.print("\n", chunk.content.lstrip(), sep="", end="")
            elif isinstance(chunk, ToolCallChunk):
                t1 = time.perf_counter()
                if (
                    not last_chunk
                    or not isinstance(last_chunk, ToolCallChunk)
                    or chunk.id != last_chunk.id
                ):
                    dim_console.print("\n", "calling tool ", chunk.tool, sep="", end="")
                    t0 = t1
                elif chunk.content and (t1 - t0) > 0.2:
                    dim_console.print(".", end="")
                    t0 = t1
            elif isinstance(chunk, ToolResponse):
                if chunk.is_error:
                    err_console.print(chunk.response)
            last_chunk = chunk
        console.print()
    except AuthenticationError as e:
        if status:
            status.stop()
        err_console.print("Received Authentication error from Anthropic:", e)
        raise SystemExit(1)
    finally:
        agent.save(Path(config().project_root).joinpath(".droid/conversation.yaml"))


if __name__ == "__main__":
    app()
