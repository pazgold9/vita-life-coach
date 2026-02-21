"""Pydantic request/response schemas for API."""
from typing import Any, Dict, List, Optional, Union

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
class ConversationTurn(BaseModel):
    role: str
    content: str


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    activity_level: Optional[str] = None
    dietary_restrictions: Optional[str] = None
    medical_conditions: Optional[str] = None
    goals: Optional[str] = None


class ExecuteRequest(BaseModel):
    prompt: str = Field(..., description="User request")
    conversation_history: list[ConversationTurn] = Field(default_factory=list)
    profile_mode: Optional[str] = Field(default=None, description="'anonymous' to skip profile injection")


class StepRecord(BaseModel):
    module: str
    prompt: Union[Dict[str, Any], List[Any]]
    response: Union[Dict[str, Any], List[Any], str]


class ExecuteResponse(BaseModel):
    status: str  # "ok" | "error"
    error: Optional[str] = None
    response: Optional[str] = None
    steps: list[StepRecord] = Field(default_factory=list)
