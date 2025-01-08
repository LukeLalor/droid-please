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
from droid_please.conversations import latest_loc_path, next_conversation_number
from droid_please.llm import ResponseChunk, ToolCallChunk, ToolResponse, UsageSummary
from rich.console import Console
from rich.style import Style
from rich.text import Text

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
    dim_console.print("Initialized project:", droid_dir)
    agent_console.print(
        "Done. Run droid",
        Text("droid learn", style="bold magenta"),
        "so I can analyze your project structure and purpose.",
    )


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
def learn():
    """
    Analyze the project structure and learn about its organization and purpose.
    The summary will be saved to the config file for future reference.
    """
    _load_config()
    agent = Agent(
        llm=_llm(),
        boot_messages=[MessageParam(content=config().get_system_prompt(), role="system")],
    )
    execute(agent, config().learn_prompt, tool_override=[ls, read_file])

    dim_console.print("Summarizing project structure and purpose...")
    chunks = []
    for chunk in agent.stream(
        messages=[MessageParam(content=config().learn_summarize_prompt, role="user")],
        tools=[ls, read_file],
    ):
        if isinstance(chunk, ResponseChunk):
            chunks.append(chunk.content)
            agent_console.print(chunk.content, end="")
    agent_console.print()

    final_summary = "".join(chunks)
    summary_loc = Path(config().project_root).joinpath(".droid/summary.txt")
    with open(summary_loc, "w") as f:
        f.write(final_summary)
    dim_console.print("Saved summary to", summary_loc.relative_to(Path.cwd()))


@app.command()
def please(
    prompt: Annotated[List[str], typer.Argument()] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i")] = False,
):
    """
    Ask the droid to do something.
    """
    _load_config()
    agent = Agent(
        llm=_llm(),
        boot_messages=[MessageParam(content=config().get_system_prompt(), role="system")],
    )
    execution_loop(agent, interactive, " ".join(prompt) if prompt else None)


@app.command(name="continue")
def continue_(
    prompt: Annotated[List[str], typer.Argument()] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i")] = False,
    file: Annotated[Optional[Path], typer.Option("--file", "-f")] = None,
    summarize: Annotated[bool, typer.Option("--summarize", "-s")] = False,
):
    """
    Continue a conversation with the droid.
    If no conversation file is provided, continues the most recent conversation.
    """
    _load_config()
    file = file or Path(config().project_root).joinpath(".droid/conversations/latest.yaml")
    if summarize:
        agent = _summarize(file)
    else:
        try:
            agent = Agent.load(loc=file, llm=_llm())
        except FileNotFoundError:
            err_console.print(f"Conversation file not found: {file}")
            raise SystemExit(1)
    execution_loop(agent, interactive, " ".join(prompt) if prompt else None)


def _prompt():
    return typer.prompt(text=">", prompt_suffix="")


def execution_loop(agent, interactive, prompt):
    if prompt and not interactive:
        execute(agent, prompt)
    else:
        while True:
            prompt = prompt or _prompt()
            execute(agent, prompt)
            prompt = None


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


def execute(agent: Agent, command: str, tool_override: List[callable] = None):
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
            elif isinstance(chunk, UsageSummary):
                dim_console.print(f"\ntokens: input {chunk.input:,} generated {chunk.generated:,}")
            last_chunk = chunk
    except AuthenticationError as e:
        if status:
            status.stop()
        err_console.print("Received Authentication error from Anthropic:", e)
        raise SystemExit(1)
    finally:
        agent.save(latest_loc_path())
        _run_hooks(config().post_execution_hooks)


@app.command()
def summarize(
        file: Annotated[Optional[Path], typer.Option("--file", "-f")] = None,
):
    """
    Create a new summary from an existing conversation.
    """
    _load_config()
    loc = file or latest_loc_path()
    _summarize(loc).save(latest_loc_path())
    agent_console.print(
        "\nDone. Run droid",
        Text("droid continue", style="bold magenta"),
        "to continue the conversation.",
    )


def _summarize(loc):
    try:
        agent = Agent.load(loc=loc, llm=_llm())
    except FileNotFoundError:
        err_console.print("No conversation found. Run", Text("droid please", style="bold magenta"),
                          "to start a new conversation.")
        raise SystemExit(1)
    chunks = []
    for chunk in agent.stream(messages=[MessageParam(content=config().conversation_summarize_prompt, role="user")],
                              tools=[ls, read_file]):
        if isinstance(chunk, ResponseChunk):
            chunks.append(chunk.content)
            dim_console.print(chunk.content, end="")
    agent = Agent(llm=_llm(),
                  boot_messages=[MessageParam(content=config().get_system_prompt(pcs="".join(chunks)), role="system")])
    return agent


@app.command()
def save(
    file: Annotated[Optional[Path], typer.Option("--file", "-f")] = None,
):
    """
    Save a version of the latest conversation. If no conversation file is provided, saves the most recent conversation.
    """
    _load_config()
    try:
        agent = Agent.load(loc=latest_loc_path(), llm=None)
    except FileNotFoundError:
        err_console.print("Conversation not found")
        raise SystemExit(1)
    save_loc = file or next_conversation_number()
    agent.save(save_loc)
    print_loc = (
        save_loc.relative_to(Path.cwd()) if save_loc.is_relative_to(Path.cwd()) else save_loc
    )
    dim_console.print("Saved conversation to", print_loc)


if __name__ == "__main__":
    app()
