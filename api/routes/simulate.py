"""Simulate route — POST /api/v1/simulate."""

from __future__ import annotations

from fastapi import APIRouter

from api.models.schemas import PersonaSentiment, SimulateRequest, SimulationResult
from engine.data.aggregator import MarketDataAggregator
from engine.sim.runner import run_simulation

router = APIRouter()

_PERSONAS = ["retail_bull", "retail_bear", "whale", "algo"]


@router.post("/simulate", response_model=SimulationResult)
async def simulate(request: SimulateRequest) -> SimulationResult:
    """Run a crowd simulation for the given ticker and catalyst.

    Fetches live market context (price, volume, Reddit, options) before
    running the simulation so the engine can adjust the catalyst bias
    based on real-world signals. If the context fetch fails for any
    reason the simulation still runs without market enrichment.

    Args:
        request: Validated :class:`SimulateRequest` payload.

    Returns:
        A :class:`SimulationResult` with per-persona breakdowns,
        aggregate directional probabilities, and live market data fields.
    """
    ticker = request.ticker.upper()

    # --- Live market context (graceful degradation on failure) ---------
    market_context = None
    try:
        market_context = MarketDataAggregator().fetch_context(ticker)
    except Exception:
        pass  # simulation will run without context enrichment

    # --- Core simulation -----------------------------------------------
    sim_result = run_simulation(
        ticker=ticker,
        catalyst=request.catalyst,
        horizon_minutes=request.horizon_minutes,
        market_context=market_context,
    )

    # --- Build response ------------------------------------------------
    total_agents = int(sim_result.get("agent_count", 0))
    bullish_count = int(sim_result.get("up_count", 0))
    bearish_count = int(sim_result.get("down_count", 0))

    if total_agents > 0:
        probability_up = bullish_count / total_agents
        probability_down = bearish_count / total_agents
    else:
        probability_up = 0.0
        probability_down = 0.0

    persona_counts = sim_result.get("persona_counts", {})
    persona_mean_stance = sim_result.get("persona_mean_stance", {})
    persona_mean_confidence = sim_result.get("persona_mean_confidence", {})

    personas: list[PersonaSentiment] = []
    for persona in _PERSONAS:
        stance = float(persona_mean_stance.get(persona, 0.0))
        count = int(persona_counts.get(persona, 0))
        weight = (count / total_agents) if total_agents > 0 else 0.0
        confidence = float(persona_mean_confidence.get(persona, 0.0))
        personas.append(
            PersonaSentiment(
                persona=persona,
                stance=stance,
                confidence=confidence,
                weight=weight,
            )
        )

    return SimulationResult(
        ticker=ticker,
        catalyst=request.catalyst,
        horizon_minutes=request.horizon_minutes,
        aggregate_stance=float(sim_result.get("mean_stance", 0.0)),
        probability_up=probability_up,
        probability_down=probability_down,
        personas=personas,
        # Market context fields (None when context fetch failed)
        current_price=market_context.current_price if market_context else None,
        volume_vs_avg=market_context.volume_vs_avg if market_context else None,
        reddit_mentions=market_context.reddit_mentions if market_context else None,
        reddit_sentiment=market_context.reddit_sentiment if market_context else None,
    )
