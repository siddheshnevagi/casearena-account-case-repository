import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from app.models.case import CaseType, Difficulty


class CaseOut(BaseModel):
    id: int
    title: str
    case_type: CaseType
    difficulty: Difficulty
    industry: str | None
    tags: list[str]
    contributor: str
    is_shared: bool
    practice_count: int
    original_filename: str
    file_size_bytes: int
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    items: list[CaseOut]
    total: int
    page: int
    page_size: int
    is_empty: bool


class CaseUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    case_type: CaseType | None = None
    difficulty: Difficulty | None = None
    industry: str | None = None
    tags: list[str] | None = None


class ModerateRequest(BaseModel):
    removal_reason: str = Field(min_length=1, max_length=1000)


SortOption = Literal["newest", "most_practiced"]
ScopeOption = Literal["community", "mine"]
