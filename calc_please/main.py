import os
import time

import typer
import readline

from anthropic.types import MessageParam
from calc_please.agent import Agent
from calc_please.llm import AnthropicLLM
from calc_please.config import load_config, config

assert readline  # importing this allows better cli experience, assertion to prevent optimize imports from removing it

from rich.console import Console
from rich.style import Style


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
    Calculator, your coding ai assistant
    """
    pass


@app.command()
def please():
    """
    Ask the calculator to do something.
    """
    agent = None
    while True:
        command = typer.prompt(text=">", prompt_suffix="")
        status = console.status("thinking...")
        status.start()
        agent = agent or Agent(
            llm=AnthropicLLM(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model=config().model,
                max_tokens=config().max_tokens,
            )
        )
        for chunk in agent.stream([MessageParam(content=command, role="user")]):
            status.stop()
            agent_console.print(chunk.content, end="")
        # add newline
        agent_console.print()


if __name__ == "__main__":
    app()
