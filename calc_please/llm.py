import os
from abc import ABC
from typing import TypeVar, Type, Any, List, Dict, Generator, Iterable

from anthropic import Anthropic, TextEvent
from anthropic.types import MessageParam, ToolParam
from calc_please.config import CONFIG
from pydantic import BaseModel

T = TypeVar("T")


class ResponseChunk(BaseModel):
    content: str


class ToolCall(BaseModel):
    id: str
    tool: str
    args: List[Any]
    kwargs: Dict[str, Any]


class ToolResponse(BaseModel):
    id: str
    response: str


class LLM(ABC):
    def execute(
        self,
        messages: Iterable[MessageParam],
        tools: Iterable[ToolParam] = None,
        output: Type[T] = str,
    ) -> List[ToolCall] | T:
        ...

    def stream(
        self, messages: List[MessageParam], tools: List[ToolParam]
    ) -> Generator[ToolCall | ResponseChunk, None, None]:
        ...


class AnthropicLLM(LLM):
    client: Anthropic

    def __init__(
        self,
        api_key: str = os.environ.get("ANTHROPIC_API_KEY"),
        model=CONFIG.model,
        max_tokens=CONFIG.max_tokens,
    ):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def stream(
        self, messages: List[MessageParam], tools: List[ToolParam]
    ) -> Generator[ToolCall | ResponseChunk, None, None]:
        kwargs = {}
        if messages and messages[0].get('role') == "system":
            kwargs['system'] = messages[0]['content']
            messages = messages[1:]
        with self.client.messages.stream(
            messages=messages, tools=tools, model=self.model, max_tokens=self.max_tokens, **kwargs
        ) as chunk_stream:
            for chunk in chunk_stream:
                if isinstance(chunk, TextEvent):
                    yield ResponseChunk(content=chunk.text)
