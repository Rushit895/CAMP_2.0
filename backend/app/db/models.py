"""ORM models — a course, its outcomes, and the audit-grade CO·PO matrix cells.

Every CSAS cell is stored with its full derivation (raw/semantic/lexical/gate/
matched terms/rationale) so a saved matrix is as explainable as a freshly computed
one — which is the point for an accreditation audit.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Course(Base):
    __tablename__ = "courses"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256))
    branch: Mapped[str | None] = mapped_column(String(128), nullable=True)
    semester: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    outcomes: Mapped[list["CourseOutcome"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="CourseOutcome.position",
    )


class CourseOutcome(Base):
    __tablename__ = "course_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(
        ForeignKey("courses.code", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)  # 0-based order within the course
    text: Mapped[str] = mapped_column(Text)
    bloom_level: Mapped[int] = mapped_column(Integer)

    course: Mapped[Course] = relationship(back_populates="outcomes")
    cells: Mapped[list["CoPoCell"]] = relationship(
        back_populates="outcome",
        cascade="all, delete-orphan",
        order_by="CoPoCell.id",
    )


class CoPoCell(Base):
    __tablename__ = "co_po_cells"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    outcome_id: Mapped[int] = mapped_column(
        ForeignKey("course_outcomes.id", ondelete="CASCADE"), index=True
    )
    po: Mapped[str] = mapped_column(String(8))
    level: Mapped[int] = mapped_column(Integer)
    raw: Mapped[float] = mapped_column(Float)
    semantic: Mapped[float] = mapped_column(Float)
    lexical: Mapped[float] = mapped_column(Float)
    gate: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text)
    matched_terms: Mapped[list] = mapped_column(JSON, default=list)

    outcome: Mapped[CourseOutcome] = relationship(back_populates="cells")
