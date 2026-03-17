"""Background scheduler for hourly backtesting scoring."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from engine.backtesting.scorer import score_pending_predictions

logger = logging.getLogger(__name__)


def start_scorer_scheduler() -> BackgroundScheduler:
    """Start the hourly scorer job and return the scheduler instance."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        score_pending_predictions,
        "interval",
        hours=1,
        id="backtest_scorer",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("backtest_scorer_scheduler_started")
    return scheduler
