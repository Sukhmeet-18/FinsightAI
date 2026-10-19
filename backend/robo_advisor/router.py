"""
FastAPI endpoints for the robo-advisor.

Register in main.py:
    from backend.robo_advisor.router import router as portfolio_router
    app.include_router(portfolio_router, prefix="/portfolio", tags=["portfolio"])

Endpoints:
    GET  /portfolio/questions   -> the 5 questionnaire questions
    POST /portfolio/recommend   -> full recommendation (see RecommendIn)
    POST /portfolio/reload      -> reload data/models after a data refresh
"""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from .service import RoboAdvisor

router = APIRouter()
_robo: RoboAdvisor | None = None


def get_robo() -> RoboAdvisor:
    global _robo
    if _robo is None:
        _robo = RoboAdvisor()        # loads prices + risk model once
    return _robo


class RecommendIn(BaseModel):
    capital: float = Field(..., gt=0, description="amount to invest now (Rs)")
    risk_answers: list[int] | None = Field(None, description="5 answers, each 1-4")
    profile: Literal["conservative", "balanced", "aggressive"] | None = None
    goal_amount: float | None = Field(None, gt=0, description="target amount (Rs)")
    years: float | None = Field(None, gt=0, le=40)
    monthly_contribution: float = Field(0, ge=0, description="monthly SIP top-up (Rs)")
    inflation: float = Field(0, ge=0, le=0.15, description="0.05 = goal in today's money at 5% inflation")

    @field_validator("risk_answers")
    @classmethod
    def check_answers(cls, v):
        if v is not None and (len(v) != 5 or any(a not in (1, 2, 3, 4) for a in v)):
            raise ValueError("risk_answers must be 5 numbers, each 1-4")
        return v


@router.get("/questions")
def questions():
    return RoboAdvisor.questions()


@router.post("/recommend")
def recommend(body: RecommendIn):
    if body.risk_answers is None and body.profile is None:
        raise HTTPException(422, "Send risk_answers (or a profile).")
    try:
        return get_robo().recommend(**body.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/reload")
def reload():
    get_robo().reload()
    return {"status": "reloaded"}
