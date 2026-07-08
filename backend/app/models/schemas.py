"""Pydantic request/response models for the CAMP API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ConfigOverride(BaseModel):
    """Optional per-request tuning of the CSAS engine."""
    semantic_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    lexical_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    lambda_saturation: float | None = Field(default=None, gt=0.0)
    tau1: float | None = Field(default=None, gt=0.0, lt=1.0)
    tau2: float | None = Field(default=None, gt=0.0, lt=1.0)
    tau3: float | None = Field(default=None, gt=0.0, lt=1.0)


class ScoreRequest(BaseModel):
    cos: list[str] = Field(..., min_length=1, description="Course Outcome statements")
    config: ConfigOverride | None = None


class MatchedTerm(BaseModel):
    term: str
    weight: float


class CellDetail(BaseModel):
    po: str
    title: str
    level: int
    label: str
    raw: float
    semantic: float
    lexical: float
    bloom_level: int
    gate: float
    matched_terms: list[MatchedTerm]
    rationale: str


class CORowOut(BaseModel):
    co: str
    bloom_level: int
    pos: dict[str, int]
    details: list[CellDetail]


class MatrixResponse(BaseModel):
    algorithm: str = "CSAS v1"
    matrix: list[CORowOut]


class ProgramOutcomeOut(BaseModel):
    id: str
    title: str
    description: str
    cognitive_tier: str


# ---- Persistence / course models ----

class CourseUpsertRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=256)
    cos: list[str] = Field(..., min_length=1, description="Course Outcome statements")
    branch: str | None = Field(default=None, max_length=128)
    semester: str | None = Field(default=None, max_length=64)


class CourseSummary(BaseModel):
    code: str
    title: str
    branch: str | None
    semester: str | None
    co_count: int
    updated_at: str | None


class CourseDetail(BaseModel):
    code: str
    title: str
    branch: str | None
    semester: str | None
    created_at: str | None
    updated_at: str | None
    matrix: list[CORowOut]
