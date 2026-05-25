"""Schemas de request/response para los endpoints."""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class PageContext(BaseModel):
    """Contexto de la página actual del usuario (URL + paso del formulario)."""
    url: Optional[str] = Field(None, max_length=500)
    path: Optional[str] = Field(None, max_length=200)
    title: Optional[str] = Field(None, max_length=200)
    form_step: Optional[str] = Field(None, max_length=100, description="Campo en el que está el usuario")
    time_on_field_seconds: Optional[int] = Field(None, ge=0, description="Segundos en el campo actual")


class ChatInitRequest(BaseModel):
    session_id: str = Field(..., min_length=4, max_length=100)
    page: Optional[PageContext] = None


class Suggestion(BaseModel):
    text: str
    action: str


class FormStep(BaseModel):
    selector: str
    message: str


class ChatInitResponse(BaseModel):
    greeting: str
    suggestions: list[Suggestion] = []
    form_steps: list[FormStep] = []
    session_id: str


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=4, max_length=100)
    message: str = Field(..., min_length=1, max_length=2000)
    page: Optional[PageContext] = None


class Source(BaseModel):
    document: str
    snippet: str
    score: float


class ChatResponse(BaseModel):
    reply: str
    sources: list[Source] = []
    role: Literal["assistant"] = "assistant"


class HealthResponse(BaseModel):
    status: str
    assistant: str
    version: str
    docs_indexed: int
