"""Course persistence + mapping orchestration.

Saving a course computes its full CO·PO matrix with CSAS and stores every cell.
Re-saving the same code replaces its outcomes (idempotent), so a course always
reflects its latest COs.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..core.config import DEFAULT_CONFIG, CSASConfig
from ..db.models import Course, CoPoCell, CourseOutcome
from ..engine.csas import score_co

_LEVEL_LABEL = {0: "None", 1: "Low", 2: "Medium", 3: "High"}


def upsert_course_with_mapping(
    db: Session,
    *,
    code: str,
    title: str,
    cos: list[str],
    branch: str | None = None,
    semester: str | None = None,
    cfg: CSASConfig = DEFAULT_CONFIG,
) -> Course:
    """Create or update a course, (re)compute its CSAS matrix, and persist it."""
    course = db.get(Course, code)
    if course is None:
        course = Course(code=code, title=title, branch=branch, semester=semester)
        db.add(course)
    else:
        course.title = title
        course.branch = branch
        course.semester = semester
        course.outcomes.clear()  # cascade delete-orphan clears cells too
        db.flush()

    for position, co_text in enumerate(cos):
        row = score_co(co_text, cfg)
        outcome = CourseOutcome(
            position=position, text=co_text, bloom_level=row.bloom_level
        )
        for cell in row.cells:
            outcome.cells.append(
                CoPoCell(
                    po=cell.po,
                    level=cell.level,
                    raw=round(cell.raw, 4),
                    semantic=round(cell.semantic, 4),
                    lexical=round(cell.lexical, 4),
                    gate=round(cell.gate, 4),
                    rationale=cell.rationale,
                    matched_terms=cell.matched_terms,
                )
            )
        course.outcomes.append(outcome)

    db.commit()
    return get_course(db, code)


def get_course(db: Session, code: str) -> Course | None:
    stmt = (
        select(Course)
        .where(Course.code == code)
        .options(selectinload(Course.outcomes).selectinload(CourseOutcome.cells))
    )
    return db.execute(stmt).scalar_one_or_none()


def list_courses(db: Session) -> list[Course]:
    stmt = select(Course).options(selectinload(Course.outcomes)).order_by(Course.updated_at.desc())
    return list(db.execute(stmt).scalars())


def delete_course(db: Session, code: str) -> bool:
    course = db.get(Course, code)
    if course is None:
        return False
    db.delete(course)
    db.commit()
    return True


def serialize_course(course: Course) -> dict:
    """Full course payload including the stored CO·PO matrix with explainability."""
    matrix = []
    for outcome in course.outcomes:
        details = [
            {
                "po": c.po,
                "title": _po_title(c.po),
                "level": c.level,
                "label": _LEVEL_LABEL[c.level],
                "raw": c.raw,
                "semantic": c.semantic,
                "lexical": c.lexical,
                "bloom_level": outcome.bloom_level,
                "gate": c.gate,
                "matched_terms": c.matched_terms or [],
                "rationale": c.rationale,
            }
            for c in outcome.cells
        ]
        matrix.append(
            {
                "co": outcome.text,
                "bloom_level": outcome.bloom_level,
                "pos": {c.po: c.level for c in outcome.cells},
                "details": details,
            }
        )
    return {
        "code": course.code,
        "title": course.title,
        "branch": course.branch,
        "semester": course.semester,
        "created_at": course.created_at.isoformat() if course.created_at else None,
        "updated_at": course.updated_at.isoformat() if course.updated_at else None,
        "matrix": matrix,
    }


def serialize_summary(course: Course) -> dict:
    return {
        "code": course.code,
        "title": course.title,
        "branch": course.branch,
        "semester": course.semester,
        "co_count": len(course.outcomes),
        "updated_at": course.updated_at.isoformat() if course.updated_at else None,
    }


# PO titles come from the engine's loaded definitions (single source of truth).
from functools import lru_cache


@lru_cache(maxsize=1)
def _po_titles() -> dict[str, str]:
    from ..engine.lexicon import load_program_outcomes

    return {po.id: po.title for po in load_program_outcomes()}


def _po_title(po_id: str) -> str:
    return _po_titles().get(po_id, po_id)
