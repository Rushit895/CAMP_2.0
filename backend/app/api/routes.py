"""API routes for CAMP2.O — the CSAS CO-PO mapping service."""
from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, HTTPException

from ..core.config import DEFAULT_CONFIG, CSASConfig
from ..engine.csas import score_matrix
from ..engine.lexicon import load_program_outcomes
from ..models.schemas import (
    MatrixResponse,
    ProgramOutcomeOut,
    ScoreRequest,
)

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
    """Score Course Outcomes against PO1-PO12 with the CSAS engine."""
    cfg = _build_config(req)
    rows = score_matrix(req.cos, cfg)
    return MatrixResponse(matrix=[row.to_dict() for row in rows])
