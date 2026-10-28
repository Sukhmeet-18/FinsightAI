from fastapi import APIRouter, HTTPException

from . import service
from ..rag.ingest import normalise_ticker

router = APIRouter()


@router.get("/summary")
def summary():
    """Say vs. Show for every company analysed (read from the saved results, so it is instant)."""
    try:
        return service.load()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.get("/{ticker}")
def one(ticker: str):
    t = normalise_ticker(ticker)
    try:
        data = service.load()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    for c in data["companies"]:
        if c["ticker"] == t:
            return c
    raise HTTPException(404, f"No Say vs. Show result for {t}.")
