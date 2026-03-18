"""api.routes — route package for the Crowd Signal API."""

from .accuracy import router as accuracy_router
from .simulate import router as simulate_router
from .tickers import router as tickers_router
from .ws_simulate import router as ws_simulate_router

__all__ = ["simulate_router", "tickers_router", "accuracy_router", "ws_simulate_router"]
