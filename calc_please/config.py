from pydantic import BaseModel


class Config(BaseModel):
    model: str = "claude-3-5-sonnet-latest"
    max_tokens: int = 8192


CONFIG = Config()
