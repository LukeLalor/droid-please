from abc import ABC
from typing import TypeVar, Type, List, Generator, Iterable, Any, Optional

from anthropic import Anthropic, TextEvent, InputJsonEvent
from anthropic.types import (
    MessageParam,
    ToolParam,
    RawContentBlockStartEvent,
    TextBlock,
    ToolUseBlock,
    MessageStopEvent
)
from pydantic import BaseModel

T = TypeVar("T")


class ResponseChunk(BaseModel):
    content: str


class ToolCallChunk(BaseModel):
    id: str
    tool: str
    content: str


class ToolResponse(BaseModel):
    id: str
    response: Any
    is_error: bool


class UsageSummary(BaseModel):
    input: int
    generated: int


class LLM(ABC):
    def execute(
        self,
        messages: Iterable[MessageParam],
        tools: Iterable[ToolParam] = None,
        output: Type[T] = str,
    ) -> List[ToolCallChunk] | T:
        ...

    def stream(
        self, messages: List[MessageParam], tools: List[ToolParam]
    ) -> Generator[ToolCallChunk | ResponseChunk, None, None]:
        ...


class AnthropicLLM(LLM):
    client: Anthropic

    def __init__(
        self,
        api_key,
        model,
        max_tokens,
    ):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def stream(
        self, messages: List[MessageParam], tools: List[ToolParam]
    ) -> Generator[ToolCallChunk | ResponseChunk, None, None]:
        kwargs, messages = self._messages(messages)
        with self.client.messages.stream(
            messages=messages,
            tools=tools,
            model=self.model,
            max_tokens=self.max_tokens,
            **kwargs,
        ) as chunk_stream:
            block: Optional[RawContentBlockStartEvent] = None
            chunks = []
            for chunk in chunk_stream:
                chunks.append(chunk)
                if isinstance(chunk, RawContentBlockStartEvent):
                    block = chunk
                elif block and isinstance(block.content_block, TextBlock) and isinstance(chunk, TextEvent):
                    yield ResponseChunk(content=chunk.text)
                elif block and isinstance(block.content_block, ToolUseBlock) and isinstance(chunk, InputJsonEvent):
                    yield ToolCallChunk(
                        id=block.content_block.id,
                        tool=block.content_block.name,
                        content=chunk.partial_json,
                    )
                elif isinstance(chunk, MessageStopEvent):
                    yield UsageSummary(input=chunk.message.usage.input_tokens, generated=chunk.message.usage.output_tokens)

    @staticmethod
    def _messages(messages):
        kwargs = {}
        if messages and messages[0].get("role") == "system":
            kwargs["system"] = messages[0]["content"]
            messages = messages[1:]
        return kwargs, messages
