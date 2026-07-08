"""Persistence tests — use a throwaway SQLite file, exercise the course service
and the API together. Pure stdlib unittest + FastAPI TestClient.

Run:  python -m unittest discover -s tests   (from backend/)
"""
from __future__ import annotations

import os
import tempfile
import unittest

# Point the app at a temp DB BEFORE importing anything that builds the engine.
_TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP.close()
os.environ["CAMP_DB_URL"] = f"sqlite:///{_TMP.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.database import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import course_service  # noqa: E402

# Create tables once for the whole module. TestClient(app) does not fire the
# lifespan startup unless entered as a context manager, so do it explicitly.
init_db()

SAMPLE_COS = [
    "Design and develop a software system using modern engineering tools.",
    "Analyze the time complexity of algorithms.",
]


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        course_service.delete_course(self.db, "T-CODE")
        self.db.close()

    def test_upsert_creates_course_with_matrix(self):
        course = course_service.upsert_course_with_mapping(
            self.db, code="T-CODE", title="Test Course", cos=SAMPLE_COS, branch="CSE",
        )
        payload = course_service.serialize_course(course)
        self.assertEqual(payload["code"], "T-CODE")
        self.assertEqual(len(payload["matrix"]), 2)
        # PO3 should be strong for the design CO
        self.assertGreaterEqual(payload["matrix"][0]["pos"]["PO3"], 2)
        # every cell persisted with 12 POs and full detail
        self.assertEqual(len(payload["matrix"][0]["details"]), 12)

    def test_reupsert_replaces_outcomes(self):
        course_service.upsert_course_with_mapping(
            self.db, code="T-CODE", title="v1", cos=SAMPLE_COS)
        course = course_service.upsert_course_with_mapping(
            self.db, code="T-CODE", title="v2", cos=["Communicate results in reports."])
        payload = course_service.serialize_course(course)
        self.assertEqual(payload["title"], "v2")
        self.assertEqual(len(payload["matrix"]), 1)  # old 2 COs gone

    def test_matched_terms_roundtrip(self):
        course = course_service.upsert_course_with_mapping(
            self.db, code="T-CODE", title="t", cos=[SAMPLE_COS[0]])
        po3 = next(c for c in course_service.serialize_course(course)["matrix"][0]["details"]
                   if c["po"] == "PO3")
        self.assertTrue(any(t["term"] == "design" for t in po3["matched_terms"]))


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def tearDown(self):
        self.client.delete("/api/courses/API-1")

    def test_full_crud_flow(self):
        # create
        r = self.client.post("/api/courses", json={
            "code": "API-1", "title": "Data Structures", "cos": SAMPLE_COS, "branch": "CSE"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(len(r.json()["matrix"]), 2)

        # list
        r = self.client.get("/api/courses")
        codes = [c["code"] for c in r.json()]
        self.assertIn("API-1", codes)

        # get
        r = self.client.get("/api/courses/API-1")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["title"], "Data Structures")

        # delete
        r = self.client.delete("/api/courses/API-1")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get("/api/courses/API-1").status_code, 404)

    def test_get_missing_returns_404(self):
        self.assertEqual(self.client.get("/api/courses/NOPE").status_code, 404)

    def test_stateless_map_still_works(self):
        r = self.client.post("/api/map", json={"cos": ["Design a system."]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["algorithm"], "CSAS v1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
