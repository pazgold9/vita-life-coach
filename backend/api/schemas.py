"""Pydantic request/response schemas for API."""
from typing import Any, Optional

from pydantic import BaseModel, Field


# --- Team info ---
class Student(BaseModel):
    name: str
    email: str


class TeamInfoResponse(BaseModel):
    group_batch_order_number: str
    team_name: str
    students: list[Student]


# --- Agent info ---
class PromptTemplate(BaseModel):
    template: str


class PromptExample(BaseModel):
    prompt: str
    full_response: str
    steps: list[dict[str, Any]]


class AgentInfoResponse(BaseModel):
    description: str
    purpose: str
    prompt_template: PromptTemplate
    prompt_examples: list[PromptExample]


# --- Execute ---
class ExecuteRequest(BaseModel):
    prompt: str = Field(..., description="User request")


class StepRecord(BaseModel):
    module: str
    prompt: dict[str, Any] | list[Any]
    response: dict[str, Any] | list[Any] | str


class ExecuteResponse(BaseModel):
    status: str  # "ok" | "error"
    error: Optional[str] = None
    response: Optional[str] = None
    steps: list[StepRecord] = Field(default_factory=list)
