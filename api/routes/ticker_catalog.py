"""Re-export ticker catalog for api.routes package compatibility."""

from api.ticker_catalog import ALLOWED_TICKERS, TICKERS

__all__ = ["TICKERS", "ALLOWED_TICKERS"]
