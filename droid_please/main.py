import os
import readline

import typer
from anthropic.types import MessageParam
from rich.console import Console
from rich.style import Style
from droid_please.agent import Agent
from droid_please.config import load_config, config
from droid_please.llm import AnthropicLLM, ResponseChunk, ToolCallChunk
from droid_please.tools import read_file

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
def please():
    """
    Ask the droid to do something.
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
        active_tool_calls = []
        for chunk in agent.stream(
            messages=[MessageParam(content=command, role="user")],
            tools=[read_file],
        ):
            if isinstance(chunk, ResponseChunk):
                if status:
                    status.stop()
                    status = None
                agent_console.print(chunk.content, end="")
            elif isinstance(chunk, ToolCallChunk):
                if chunk.tool not in active_tool_calls:
                    active_tool_calls.append(chunk.tool)
                    if status:
                        status.update(
                            f"calling tool(s): {', '.join(active_tool_calls)}"
                        )
                    else:
                        status = console.status(
                            f"calling tools: {', '.join(active_tool_calls)}"
                        )
                        status.start()
        agent_console.print()


if __name__ == "__main__":
    app()
