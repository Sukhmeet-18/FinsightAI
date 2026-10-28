from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import store
from .ingest import normalise_ticker
from .llm import LLMError
from .service import RagService

router = APIRouter()
_state = {}


def get_service():
    if "svc" not in _state:
        _state["svc"] = RagService()
    return _state["svc"]


class AskIn(BaseModel):
    ticker: str
    question: str


@router.get("/companies")
def companies():
    """Which companies have a search index built."""
    return [store.info(t) for t in store.available()]


@router.post("/ask")
def ask(body: AskIn):
    ticker = normalise_ticker(body.ticker)
    try:
        return get_service().ask(ticker, body.question)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except LLMError as e:
        raise HTTPException(503, str(e))
    except ImportError as e:
        raise HTTPException(503, f"A package needed for search is missing ({e}). Run: pip install -r requirements-rag.txt")
