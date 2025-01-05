from __future__ import annotations

import copy
from typing import List, Generator

import yaml
from anthropic.types import MessageParam
from calc_please.llm import LLM, ToolCall, ResponseChunk, ToolResponse


class Agent:
    def __init__(self, llm: LLM, boot_messages: List[MessageParam] = None):
        self._llm = llm
        self.boot_messages = boot_messages or []
        self.messages = []

    def _make_tools(self, tools: List[callable]):
        # todo: make tools
        return []

    def stream(
        self,
        messages: List[MessageParam],
        tools: List[callable] = None,
        boot_override: List[MessageParam] = None,
    ) -> Generator[ResponseChunk | ToolCall | ToolResponse, None, None]:
        self.messages.extend(messages)
        boot_messages = self.boot_messages if boot_override is None else boot_override
        tools = self._make_tools(tools) if tools else []
        started, tool_calls = False, []
        while not started or tool_calls:
            for tc in tool_calls:
                raise NotImplementedError("tool calls not yet implemented")
            agent_response = []
            for chunk in self._llm.stream(
                messages=boot_messages + self.messages, tools=tools
            ):
                started = True
                if isinstance(chunk, ToolCall):
                    tool_calls.append(chunk)
                elif isinstance(chunk, ResponseChunk):
                    agent_response.append(chunk)
                else:
                    raise NotImplementedError("unknown chunk type")
                yield chunk
            agent_response = MessageParam(
                content="".join([r.content for r in agent_response]), role="assistant"
            )
            self.messages.append(agent_response)

    def clone(self) -> Agent:
        return Agent(
            llm=self._llm,
            boot_messages=copy.deepcopy(self.boot_messages),
        )

    def save(self, location: str):
        with open(location, "w") as f:
            yaml.dump(
                dict(boot_messages=self.boot_messages, messages=self.messages),
                f,
                sort_keys=False,
            )

    @staticmethod
    def load(location: str, llm: LLM) -> Agent:
        with open(location, "r") as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
        agent = Agent(llm=llm, boot_messages=data["boot_messages"])
        agent.messages = data["messages"]
        return agent
