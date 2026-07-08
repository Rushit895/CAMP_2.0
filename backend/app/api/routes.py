"""API routes for CAMP2.O — the CSAS CO-PO mapping service."""
from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.config import DEFAULT_CONFIG, CSASConfig
from ..db.database import get_db
from ..engine.csas import score_matrix
from ..engine.lexicon import load_program_outcomes
from ..models.schemas import (
    CourseDetail,
    CourseSummary,
    CourseUpsertRequest,
    MatrixResponse,
    ProgramOutcomeOut,
    ScoreRequest,
)
from ..services import course_service

router = APIRouter()


def _build_config(req: ScoreRequest) -> CSASConfig:
    if req.config is None:
        return DEFAULT_CONFIG
    overrides = {k: v for k, v in req.config.model_dump().items() if v is not None}
    cfg = replace(DEFAULT_CONFIG, **overrides)
    try:
        cfg.validate()
    except AssertionError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid config: {exc}") from exc
    return cfg


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "algorithm": "CSAS v1"}


@router.get("/program-outcomes", response_model=list[ProgramOutcomeOut])
def program_outcomes() -> list[ProgramOutcomeOut]:
    return [
        ProgramOutcomeOut(
            id=po.id, title=po.title, description=po.description,
            cognitive_tier=po.cognitive_tier,
        )
        for po in load_program_outcomes()
    ]


@router.post("/map", response_model=MatrixResponse)
def map_cos(req: ScoreRequest) -> MatrixResponse:
    """Score Course Outcomes against PO1-PO12 with the CSAS engine (stateless)."""
    cfg = _build_config(req)
    rows = score_matrix(req.cos, cfg)
    return MatrixResponse(matrix=[row.to_dict() for row in rows])


# ---- Course persistence (stateful) ----

@router.post("/courses", response_model=CourseDetail)
def upsert_course(req: CourseUpsertRequest, db: Session = Depends(get_db)) -> dict:
    """Create/update a course, compute its CSAS matrix, and persist it."""
    course = course_service.upsert_course_with_mapping(
        db, code=req.code, title=req.title, cos=req.cos,
        branch=req.branch, semester=req.semester,
    )
    return course_service.serialize_course(course)


@router.get("/courses", response_model=list[CourseSummary])
def list_courses(db: Session = Depends(get_db)) -> list[dict]:
    return [course_service.serialize_summary(c) for c in course_service.list_courses(db)]


@router.get("/courses/{code}", response_model=CourseDetail)
def get_course(code: str, db: Session = Depends(get_db)) -> dict:
    course = course_service.get_course(db, code)
    if course is None:
        raise HTTPException(status_code=404, detail=f"Course {code!r} not found")
    return course_service.serialize_course(course)


@router.delete("/courses/{code}")
def delete_course(code: str, db: Session = Depends(get_db)) -> dict:
    if not course_service.delete_course(db, code):
        raise HTTPException(status_code=404, detail=f"Course {code!r} not found")
    return {"deleted": code}
