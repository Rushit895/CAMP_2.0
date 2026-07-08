"""Seed a couple of demo courses on first startup.

Free hosting tiers have an ephemeral filesystem, so the SQLite DB resets on each
restart. Seeding when the DB is empty means a visitor always lands on a populated
dashboard (dropdown + a rendered matrix) instead of a blank page — and it self-heals
after every restart. No-op once any course exists, so it never clobbers real data.
"""
from __future__ import annotations

from sqlalchemy import select

from ..services import course_service
from .database import SessionLocal
from .models import Course

_DEMOS = [
    {
        "code": "B22EF0504",
        "title": "Machine Learning and Applications",
        "branch": "CSE",
        "semester": "5",
        "cos": [
            "Understand basics of Artificial Intelligence and Machine Learning.",
            "Apply supervised learning algorithm for regression and classification problems.",
            "Use unsupervised learning algorithms to identify patterns and structure in unlabelled datasets.",
            "Analyze real world applications using supervised and unsupervised learning algorithms.",
            "Analyze the performance of machine learning models using different evaluation metrics.",
            "Explain dimensionality reduction algorithms and its applications.",
        ],
    },
    {
        "code": "21CS42",
        "title": "Data Structures & Algorithms",
        "branch": "CSE",
        "semester": "4",
        "cos": [
            "Apply data structures and algorithms to solve computational problems efficiently.",
            "Analyze the time complexity and space complexity of algorithms.",
            "Design and develop a software system using modern engineering tools.",
            "Communicate technical results effectively through reports and presentations.",
        ],
    },
]


def seed_if_empty() -> None:
    db = SessionLocal()
    try:
        if db.execute(select(Course).limit(1)).first() is not None:
            return  # already has data — leave it alone
        for demo in _DEMOS:
            course_service.upsert_course_with_mapping(
                db,
                code=demo["code"],
                title=demo["title"],
                cos=demo["cos"],
                branch=demo["branch"],
                semester=demo["semester"],
            )
    finally:
        db.close()
