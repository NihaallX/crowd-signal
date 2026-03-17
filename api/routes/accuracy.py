"""Accuracy routes — GET /api/v1/accuracy and /api/v1/accuracy/{ticker}."""

from __future__ import annotations

from fastapi import APIRouter

from api.models.schemas import AccuracyStats, TickerAccuracyEntry
from engine.backtesting.scorer import get_accuracy_stats, get_ticker_accuracy

router = APIRouter()


@router.get("/accuracy", response_model=AccuracyStats)
async def accuracy() -> AccuracyStats:
    payload = get_accuracy_stats()
    return AccuracyStats(
        global_accuracy=payload.get("global_accuracy", {"total": 0, "correct": 0, "accuracy_pct": 0.0}),
        by_ticker=payload.get("by_ticker", {}),
        last_updated=str(payload.get("last_updated", "")),
    )


@router.get("/accuracy/{ticker}", response_model=TickerAccuracyEntry)
async def accuracy_ticker(ticker: str) -> TickerAccuracyEntry:
    payload = get_ticker_accuracy(ticker.upper())
    return TickerAccuracyEntry(
        total=int(payload.get("total", 0)),
        correct=int(payload.get("correct", 0)),
        accuracy_pct=float(payload.get("accuracy_pct", 0.0)),
    )
