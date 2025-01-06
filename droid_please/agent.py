from __future__ import annotations

import glob
import copy
import json
from os import PathLike
from pathlib import Path
from typing import List, Generator, Callable, Dict, Optional

import yaml
from anthropic.types import (
    MessageParam,
    ToolParam,
    ToolResultBlockParam,
    ToolUseBlockParam,
    TextBlockParam,
)

from droid_please.config import config
from droid_please.llm import LLM, ToolCallChunk, ResponseChunk, ToolResponse
from droid_please.util import callable_params_as_json_schema, SchemaWrapper


class Agent:
    def __init__(self, llm: LLM, boot_messages: List[MessageParam] = None):
        self._llm = llm
        self.boot_messages = boot_messages or []
        self.messages = []
        self.conversation_loc: Optional[Path] = None
        self._last_used_tools: List[dict] = []

    def stream(
        self,
        messages: List[MessageParam],
        tools: List[Callable] = None,
        boot_override: List[MessageParam] = None,
    ) -> Generator[ResponseChunk | ToolCallChunk | ToolResponse, None, None]:
        self.messages.extend(messages)
        boot_messages = self.boot_messages if boot_override is None else boot_override
        tools: Dict[str, ToolWrapper] = {
            tw.name: tw for tw in (ToolWrapper(t) for t in tools or [])
        }
        self._last_used_tools = [t.tool for t in tools.values()]
        while True:
            agent_response = []
            for chunk in self._llm.stream(
                messages=boot_messages + self.messages,
                tools=[tw.tool for tw in tools.values()],
            ):
                if isinstance(chunk, ToolCallChunk):
                    if (
                        not agent_response
                        or not isinstance(agent_response[-1][-1], ToolCallChunk)
                        or not agent_response[-1][-1].id == chunk.id
                    ):
                        agent_response.append([])
                    agent_response[-1].append(chunk)
                elif isinstance(chunk, ResponseChunk):
                    if not agent_response or not isinstance(agent_response[-1][-1], ResponseChunk):
                        agent_response.append([])
                    agent_response[-1].append(chunk)
                else:
                    raise NotImplementedError("unknown chunk type")
                yield chunk
            if len(agent_response) == 1 and isinstance(agent_response[0][0], ResponseChunk):
                join = "".join([r.content for r in agent_response[0]])
                self.messages.append(MessageParam(content=join, role="assistant"))
                break
            else:
                tool_responses: List[ToolResultBlockParam] = []
                block_acc: List[TextBlockParam | ToolUseBlockParam] = []
                for block in agent_response:
                    if isinstance(block[0], ResponseChunk):
                        block_acc.append(
                            TextBlockParam(
                                type="text",
                                text="".join([r.content for r in block]),
                            )
                        )
                    elif isinstance(block[0], ToolCallChunk):
                        # todo consider what to do if this fails. needs to be valid dict to send back to llm
                        tc_args = ToolWrapper.args(block)
                        try:
                            tool_response = tools[block[0].tool].execute(tc_args)
                            is_error = False
                        except Exception as e:
                            tool_response = e
                            is_error = True
                        block_acc.append(
                            ToolUseBlockParam(
                                id=block[0].id,
                                input=tc_args,
                                name=block[0].tool,
                                type="tool_use",
                            )
                        )
                        try:
                            tool_response_str = (
                                yaml.dump(tool_response, allow_unicode=True)
                                if not isinstance(tool_response, str)
                                else tool_response
                            )
                        except Exception as e:
                            tool_response_str = str(e)
                        tool_responses.append(
                            ToolResultBlockParam(
                                tool_use_id=block[0].id,
                                type="tool_result",
                                content=tool_response_str,
                                is_error=is_error,
                            )
                        )
                        yield ToolResponse(
                            id=block[0].id,
                            response=tool_response,
                            is_error=is_error,
                        )
                    else:
                        raise NotImplementedError("unknown chunk type")
                self.messages.append(
                    MessageParam(
                        role="assistant",
                        content=block_acc,
                    )
                )
                self.messages.append(
                    MessageParam(
                        role="user",
                        content=tool_responses,
                    )
                )

    def clone(self) -> Agent:
        return Agent(
            llm=self._llm,
            boot_messages=copy.deepcopy(self.boot_messages),
        )

    @staticmethod
    def _get_next_conversation_number(base_dir: str | PathLike) -> Path:
        """Get the next conversation number based on existing files."""
        conv_dir = Path(base_dir).joinpath("conversations")
        existing_files = glob.glob(str(conv_dir.joinpath("*.yaml")))
        if not existing_files:
            return conv_dir.joinpath("0001.yaml")
        numbers = [int(Path(f).stem) for f in existing_files]
        return conv_dir.joinpath(f"{max(numbers) + 1:04d}.yaml")

    def save(self, base_dir: str | PathLike):
        conv_dir = Path(base_dir).joinpath("conversations")
        conv_dir.mkdir(exist_ok=True)

        if not self.conversation_loc:
            self.conversation_loc = self._get_next_conversation_number(base_dir)

        self.conversation_loc.parent.mkdir(exist_ok=True)
        with open(conv_dir.joinpath(self.conversation_loc), "w") as f:
            yaml.dump(
                dict(
                    boot_messages=self.boot_messages,
                    messages=self.messages,
                    tools=self._last_used_tools,
                ),
                f,
                sort_keys=False,
                default_style="|",
                allow_unicode=True,
            )

    @staticmethod
    def load(loc: str | PathLike, llm: LLM) -> Agent:
        if not loc:
            # Get the latest conversation file
            conversation_dir = Path(config().project_root).joinpath(".droid/conversations")
            pattern = str(conversation_dir.joinpath("*.yaml"))
            conv_files = glob.glob(pattern)
            if not conv_files:
                raise FileNotFoundError("No conversations found")
            loc = max(
                conv_files
            )  # since conversations are prefixed with numbers, this will get the latest

        with open(loc, "r") as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
        agent = Agent(llm=llm, boot_messages=data["boot_messages"])
        agent.messages = data["messages"]
        return agent


class ToolWrapper:
    _callable: Callable
    _param_schema: SchemaWrapper

    def __init__(self, fn: Callable):
        self._callable = fn
        self._param_schema = callable_params_as_json_schema(fn)

    @property
    def name(self) -> str:
        return self._callable.__name__

    @property
    def tool(self) -> ToolParam:
        return ToolParam(
            name=self._callable.__name__,
            description=self._callable.__doc__,
            input_schema=self._param_schema.schema,
        )

    @staticmethod
    def args(chunks: List[ToolCallChunk]):
        return json.loads("".join([c.content for c in chunks]) or "{}")

    def execute(self, data: dict):
        kwargs = self._param_schema.parse(data)
        return self._callable(**kwargs)
