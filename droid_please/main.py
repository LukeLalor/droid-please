import os
import readline
import time
from pathlib import Path
from typing import Annotated, Optional

import typer
from anthropic.types import MessageParam
from rich.console import Console
from rich.style import Style
from droid_please.agent import Agent
from droid_please.config import load_config, config
from droid_please.llm import AnthropicLLM, ResponseChunk, ToolCallChunk, ToolResponse
from droid_please.tools import read_file, update_file, rename_file, delete_file, ls

assert readline  # importing this allows better cli experience, assertion to prevent optimize imports from removing it

app = typer.Typer()

console = Console()
agent_console = Console(style="green italic")
dim_console = Console(style=Style(dim=True))
err_console = Console(stderr=True, style="red")

try:
    load_config()
except FileNotFoundError as e:
    err_console.print(str(e))
    raise SystemExit(1)


@app.callback()
def callback():
    """
    Droid, your coding ai assistant
    """
    pass


@app.command()
def please(command: Annotated[str, typer.Argument()] = None):
    """
    Ask the droid to do something.
    """
    agent = Agent(llm=config().llm())
    while True:
        try:
            command = command or typer.prompt(text=">", prompt_suffix="")
            execution_loop(agent, command)
            command = None
        finally:
            agent.save(Path(config().project_root).joinpath(".droid/conversation.yaml"))


@app.command(name="continue")
def continue_(command: Annotated[str, typer.Argument()] = None):
    """
    Ask the droid to do something.
    """
    agent = Agent.load(Path(config().project_root).joinpath(".droid/conversation.yaml"), llm=config().llm())
    while True:
        try:
            command = command or typer.prompt(text=">", prompt_suffix="")
            execution_loop(agent, command)
            command = None
        finally:
            agent.save(Path(config().project_root).joinpath(".droid/conversation.yaml"))


def execution_loop(agent: Agent, command: str):
    status = console.status("thinking...")
    status.start()
    last_chunk = None
    t0 = time.perf_counter()
    for chunk in agent.stream(
            messages=[MessageParam(content=command, role="user")],
            tools=[read_file, update_file, rename_file, delete_file, ls],
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
            if not last_chunk or not isinstance(last_chunk, ToolCallChunk) or chunk.id != last_chunk.id:
                dim_console.print("\n", "calling tool ", chunk.tool, sep="", end="")
            elif chunk.content and (t1 - t0) * 1000 > 200:
                dim_console.print(".", end="")
            t0 = t1
        elif isinstance(chunk, ToolResponse):
            if chunk.is_error:
                err_console.print(chunk.response)
        last_chunk = chunk
    console.print()


if __name__ == "__main__":
    app()
