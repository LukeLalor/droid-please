import os
import readline
import subprocess
import time
from pathlib import Path
from typing import Annotated, Optional, List

import typer
from anthropic import AuthenticationError
from anthropic.types import MessageParam
from droid_please.agent import Agent
from droid_please.agent_tools import (
    read_file,
    update_file,
    rename_file,
    delete_path,
    ls,
    create_file,
)
from droid_please.config import load_config, config, Config
from droid_please.llm import ResponseChunk, ToolCallChunk, ToolResponse
from rich.console import Console
from rich.style import Style

assert readline  # importing this allows better cli experience, assertion to prevent optimize imports from removing it

app = typer.Typer()

console = Console()
agent_console = Console(style="green italic")
dim_console = Console(style=Style(dim=True))
err_console = Console(stderr=True, style="red")


@app.callback()
def callback():
    """
    Droid, your coding AI assistant
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
        f.write(".env\nconversations/\n")

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
        err_console.print('Could not find .droid directory. Run "droid init" to create one.')
        raise SystemExit(1)


def _llm():
    try:
        return config().llm()
    except RuntimeError as e:
        err_console.print(str(e))
        raise SystemExit(1)


@app.command()
def learn(
    save: Annotated[bool, typer.Option("--save", "-s", help="Save conversation state")] = False,
):
    """
    Analyze the project structure and learn about its organization and purpose.
    The summary will be saved to the config file for future reference.
    """
    _load_config()
    agent = Agent(
        llm=_llm(),
        boot_messages=[MessageParam(content=config().get_system_prompt(), role="system")],
    )
    execute(agent, config().learn_prompt, save=save, tool_override=[ls, read_file])

    dim_console.print("Summarizing project structure and purpose...")
    chunks = []
    for chunk in agent.stream(
        messages=[MessageParam(content=config().summarize_prompt, role="user")],
        tools=[ls, read_file],
    ):
        if isinstance(chunk, ResponseChunk):
            chunks.append(chunk.content)
            agent_console.print(chunk.content, end="")
    agent_console.print()

    final_summary = "".join(chunks)
    with open(Path(config().project_root).joinpath(".droid/summary.txt"), "w") as f:
        f.write(final_summary)
    dim_console.print("Done.")


@app.command()
def please(
    prompt: Annotated[List[str], typer.Argument()] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i")] = False,
    save: Annotated[bool, typer.Option("--save", "-s", help="Save conversation state")] = False,
):
    """
    Ask the droid to do something.
    """
    _load_config()
    agent = Agent(
        llm=_llm(),
        boot_messages=[MessageParam(content=config().get_system_prompt(), role="system")],
    )
    execution_loop(agent, interactive, " ".join(prompt) if prompt else None, save)


@app.command(name="continue")
def continue_(
    prompt: Annotated[List[str], typer.Argument()] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i")] = False,
    conversation: Annotated[Optional[Path], typer.Option("--conversation", "-c")] = None,
    save: Annotated[bool, typer.Option("--save", "-s", help="Save conversation state")] = False,
):
    """
    Continue a conversation with the droid.
    If no conversation ID is provided, continues the most recent conversation.
    """
    _load_config()
    agent = Agent.load(loc=conversation, llm=_llm())
    execution_loop(agent, interactive, " ".join(prompt) if prompt else None, save)


def _prompt():
    return typer.prompt(text=">", prompt_suffix="")


def execution_loop(agent, interactive, prompt, save: bool = False):
    magic_words = {"droid save"}
    if not interactive:
        if not prompt:
            err_console.print("Error: prompt is required in non-interactive mode")
            raise SystemExit(1)
        execute(agent, prompt, save)
    else:
        while interactive:
            prompt = _prompt()
            while prompt in magic_words:
                if prompt == "droid save":
                    save = True
                    agent.save(Path(config().project_root).joinpath(".droid"))
                    dim_console.print("conversation saved")
                else:
                    err_console.print("Unknown Command")
                prompt = _prompt()
            execute(agent, prompt, save)


def _run_hooks(hooks: list[str]):
    for hook in hooks:
        try:
            result = subprocess.run(hook, shell=True, capture_output=True, text=True)
        except Exception as e:
            err_console.print(f"Error executing hook: {hook}")
            err_console.print(str(e))
            raise SystemExit(1)
        if result.returncode != 0:
            err_console.print(f"Hook failed: {hook}")
            err_console.print(result.stderr)
            raise SystemExit(1)


def execute(agent: Agent, command: str, save: bool = False, tool_override: List[callable] = None):
    _run_hooks(config().pre_execution_hooks)
    status = console.status("thinking...")
    status.start()
    last_chunk = None
    t0 = time.perf_counter()
    try:
        for chunk in agent.stream(
            messages=[MessageParam(content=command, role="user")],
            tools=tool_override
            or [read_file, create_file, update_file, rename_file, delete_path, ls],
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
        # Run post-execution hooks
        if save:
            agent.save(Path(config().project_root).joinpath(".droid"))
        _run_hooks(config().post_execution_hooks)


if __name__ == "__main__":
    app()
