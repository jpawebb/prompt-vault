from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Any



class PromptCreate(BaseModel):
    """Model for prompt entry creation."""
    name: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9_\-]+$")
    description: str | None = None
    template: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
 
    @field_validator("name")
    @classmethod
    def name_must_be_slug(cls, v: str) -> str:
        return v.strip().lower()
    

class PromptRead(BaseModel):
    """Model for reading prompt entries."""
    id: int
    name: str
    description: str | None
    template: str
    version: int
    tags: list[str]
    is_active: bool
    input_variables: list[str]
    created_at: datetime
 
    model_config = {"from_attributes": True}


class PromptSummary(BaseModel):
    """Lightweight version for list endpoints."""
    id: int
    name: str
    description: str | None
    version: int
    tags: list[str]
    is_active: bool
    created_at: datetime
 
    model_config = {"from_attributes": True}
 

class PromptDiff(BaseModel):
    """Represents the change in state between two versions of a prompt."""
    name: str
    version_a: int
    version_b: int
    diff_lines: list[str]



class RenderRequest(BaseModel):
    """Model for rendering a prompt with required input variables."""
    variables: dict[str, Any] = Field(default_factory=dict)


class RenderResponse(BaseModel):
    """Rendered output of prompt after processing with input variables."""
    name: str
    version: int
    rendered: str
 