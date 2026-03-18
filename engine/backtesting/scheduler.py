"""Background scheduler for hourly backtesting scoring."""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from engine.backtesting.scorer import score_pending_predictions
from engine.scanner.catalyst_scanner import run_daily_scan

logger = logging.getLogger(__name__)


def run_daily_scan_sync(market: str) -> None:
    asyncio.run(run_daily_scan(market))


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
    scheduler.add_job(
        run_daily_scan_sync,
        "cron",
        args=["IN"],
        hour=3,
        minute=15,
        day_of_week="mon-fri",
        id="daily_scan_IN",
        replace_existing=True,
    )
    scheduler.add_job(
        run_daily_scan_sync,
        "cron",
        args=["US"],
        hour=13,
        minute=0,
        day_of_week="mon-fri",
        id="daily_scan_US",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("backtest_scorer_scheduler_started")
    return scheduler
