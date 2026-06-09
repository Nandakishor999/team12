from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    role: Literal["user", "assistant"] = Field(
        ..., description="Who sent this message — must be 'user' or 'assistant'."
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Non-empty text content of the message.",
    )


class ChatRequest(BaseModel):
    """Incoming chat request from the frontend."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="The user's current question (1–4000 characters).",
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Recent conversation history sent from the client.",
    )

    @field_validator("history")
    @classmethod
    def cap_history(cls, v: list[ChatMessage]) -> list[ChatMessage]:
        """Never accept more than 20 history messages to protect token limits."""
        return v[-20:] if len(v) > 20 else v


class ChatResponse(BaseModel):
    """Outgoing chat response sent to the frontend."""

    response: str = Field(..., description="Bot reply text.")
    error: Optional[str] = Field(None, description="Non-None if a recoverable error occurred.")
