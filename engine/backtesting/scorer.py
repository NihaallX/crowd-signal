"""Backtesting scorer for 24h directional prediction accuracy."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
import yfinance as yf

logger = logging.getLogger(__name__)


def _get_connection() -> psycopg2.extensions.connection | None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return None
    try:
        return psycopg2.connect(database_url, connect_timeout=5)
    except Exception as exc:  # noqa: BLE001
        logger.warning("backtesting_db_connect_failed error=%s", exc)
        return None


def _fetch_current_price(ticker: str) -> float | None:
    try:
        data = yf.Ticker(ticker).history(period="1d", interval="1m")
        if data.empty:
            return None
        return float(data["Close"].iloc[-1])
    except Exception as exc:  # noqa: BLE001
        logger.warning("backtesting_price_fetch_failed ticker=%s error=%s", ticker, exc)
        return None


def _derive_actual_direction(price_at_simulation: float, actual_price: float) -> str:
    if price_at_simulation <= 0:
        return "neutral"
    move_pct = ((actual_price - price_at_simulation) / price_at_simulation) * 100.0
    if move_pct > 0.5:
        return "up"
    if move_pct < -0.5:
        return "down"
    return "neutral"


def _derive_predicted_direction(probability_up: float, probability_down: float) -> str:
    if probability_up > 0.55:
        return "up"
    if probability_down > 0.55:
        return "down"
    return "neutral"


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _refresh_accuracy_summary(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            WITH agg AS (
                SELECT
                    ticker,
                    COUNT(*)::int AS total_predictions,
                    COALESCE(SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END), 0)::int AS correct_predictions
                FROM simulation_runs
                WHERE prediction_correct IS NOT NULL
                GROUP BY ticker
            )
            INSERT INTO accuracy_summary (
                ticker,
                total_predictions,
                correct_predictions,
                accuracy_pct,
                last_updated
            )
            SELECT
                agg.ticker,
                agg.total_predictions,
                agg.correct_predictions,
                CASE
                    WHEN agg.total_predictions > 0
                        THEN (agg.correct_predictions::float / agg.total_predictions::float) * 100.0
                    ELSE 0.0
                END,
                NOW()
            FROM agg
            ON CONFLICT (ticker)
            DO UPDATE SET
                total_predictions = EXCLUDED.total_predictions,
                correct_predictions = EXCLUDED.correct_predictions,
                accuracy_pct = EXCLUDED.accuracy_pct,
                last_updated = NOW()
            """
        )

        cursor.execute(
            """
            SELECT
                COUNT(*)::int AS total_predictions,
                COALESCE(SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END), 0)::int AS correct_predictions
            FROM simulation_runs
            WHERE prediction_correct IS NOT NULL
            """
        )
        global_row = cursor.fetchone() or (0, 0)
        total_predictions = _safe_int(global_row[0])
        correct_predictions = _safe_int(global_row[1])
        accuracy_pct = (correct_predictions / total_predictions * 100.0) if total_predictions > 0 else 0.0

        cursor.execute("SELECT id FROM accuracy_summary_global ORDER BY last_updated DESC LIMIT 1")
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                """
                UPDATE accuracy_summary_global
                SET
                    total_predictions = %s,
                    correct_predictions = %s,
                    accuracy_pct = %s,
                    last_updated = NOW()
                WHERE id = %s
                """,
                (total_predictions, correct_predictions, accuracy_pct, existing[0]),
            )
        else:
            cursor.execute(
                """
                INSERT INTO accuracy_summary_global (
                    total_predictions,
                    correct_predictions,
                    accuracy_pct,
                    last_updated
                )
                VALUES (%s, %s, %s, NOW())
                """,
                (total_predictions, correct_predictions, accuracy_pct),
            )


def score_pending_predictions() -> dict[str, float | int]:
    """Score unscored runs from 24-48h ago and refresh summaries."""
    conn = _get_connection()
    if conn is None:
        return {"scored_count": 0, "correct_count": 0, "accuracy_pct": 0.0}

    now = datetime.now(timezone.utc)
    window_end = now - timedelta(hours=24)
    window_start = now - timedelta(hours=48)

    scored_count = 0
    correct_count = 0

    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        ticker,
                        probability_up,
                        probability_down,
                        price_at_simulation
                    FROM simulation_runs
                    WHERE created_at >= %s
                      AND created_at <= %s
                      AND actual_direction IS NULL
                      AND price_at_simulation IS NOT NULL
                    ORDER BY created_at ASC
                    """,
                    (window_start, window_end),
                )
                rows = cursor.fetchall() or []

                for row in rows:
                    try:
                        ticker = str(row.get("ticker", "")).upper()
                        if not ticker:
                            continue

                        price_at_simulation = _safe_float(row.get("price_at_simulation"))
                        if price_at_simulation <= 0:
                            continue

                        actual_price = _fetch_current_price(ticker)
                        if actual_price is None:
                            continue

                        actual_direction = _derive_actual_direction(price_at_simulation, actual_price)
                        predicted_direction = _derive_predicted_direction(
                            _safe_float(row.get("probability_up")),
                            _safe_float(row.get("probability_down")),
                        )
                        prediction_correct = predicted_direction == actual_direction

                        cursor.execute(
                            """
                            UPDATE simulation_runs
                            SET
                                actual_price_24h = %s,
                                actual_direction = %s,
                                prediction_correct = %s
                            WHERE id = %s
                            """,
                            (actual_price, actual_direction, prediction_correct, row.get("id")),
                        )

                        scored_count += 1
                        if prediction_correct:
                            correct_count += 1
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("score_run_failed run_id=%s error=%s", row.get("id"), exc)
                        continue

            _refresh_accuracy_summary(conn)

        accuracy_pct = (correct_count / scored_count * 100.0) if scored_count > 0 else 0.0
        return {
            "scored_count": scored_count,
            "correct_count": correct_count,
            "accuracy_pct": accuracy_pct,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("score_pending_predictions_failed error=%s", exc)
        return {"scored_count": 0, "correct_count": 0, "accuracy_pct": 0.0}
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass


def get_ticker_accuracy(ticker: str) -> dict[str, float | int]:
    """Fetch directional accuracy for one ticker with zero-safe fallback."""
    conn = _get_connection()
    if conn is None:
        return {"total": 0, "correct": 0, "accuracy_pct": 0.0}

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT total_predictions, correct_predictions, accuracy_pct
                FROM accuracy_summary
                WHERE ticker = %s
                LIMIT 1
                """,
                (ticker.upper(),),
            )
            row = cursor.fetchone()
            if not row:
                return {"total": 0, "correct": 0, "accuracy_pct": 0.0}
            return {
                "total": _safe_int(row.get("total_predictions")),
                "correct": _safe_int(row.get("correct_predictions")),
                "accuracy_pct": _safe_float(row.get("accuracy_pct")),
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_ticker_accuracy_failed ticker=%s error=%s", ticker, exc)
        return {"total": 0, "correct": 0, "accuracy_pct": 0.0}
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass


def get_accuracy_stats() -> dict[str, Any]:
    """Fetch global and per-ticker directional accuracy summaries."""
    conn = _get_connection()
    if conn is None:
        return {
            "global_accuracy": {"total": 0, "correct": 0, "accuracy_pct": 0.0},
            "by_ticker": {},
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT total_predictions, correct_predictions, accuracy_pct, last_updated
                FROM accuracy_summary_global
                ORDER BY last_updated DESC
                LIMIT 1
                """
            )
            global_row = cursor.fetchone()

            cursor.execute(
                """
                SELECT ticker, total_predictions, correct_predictions, accuracy_pct, last_updated
                FROM accuracy_summary
                ORDER BY total_predictions DESC, ticker ASC
                """
            )
            ticker_rows = cursor.fetchall() or []

        by_ticker: dict[str, dict[str, float | int]] = {}
        last_updated_dt: datetime | None = None

        for row in ticker_rows:
            ticker = str(row.get("ticker", "")).upper()
            if not ticker:
                continue
            by_ticker[ticker] = {
                "total": _safe_int(row.get("total_predictions")),
                "correct": _safe_int(row.get("correct_predictions")),
                "accuracy_pct": _safe_float(row.get("accuracy_pct")),
            }
            row_updated = row.get("last_updated")
            if isinstance(row_updated, datetime):
                if last_updated_dt is None or row_updated > last_updated_dt:
                    last_updated_dt = row_updated

        if global_row:
            global_accuracy = {
                "total": _safe_int(global_row.get("total_predictions")),
                "correct": _safe_int(global_row.get("correct_predictions")),
                "accuracy_pct": _safe_float(global_row.get("accuracy_pct")),
            }
            global_updated = global_row.get("last_updated")
            if isinstance(global_updated, datetime):
                if last_updated_dt is None or global_updated > last_updated_dt:
                    last_updated_dt = global_updated
        else:
            global_accuracy = {"total": 0, "correct": 0, "accuracy_pct": 0.0}

        last_updated = (last_updated_dt or datetime.now(timezone.utc)).isoformat()
        return {
            "global_accuracy": global_accuracy,
            "by_ticker": by_ticker,
            "last_updated": last_updated,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_accuracy_stats_failed error=%s", exc)
        return {
            "global_accuracy": {"total": 0, "correct": 0, "accuracy_pct": 0.0},
            "by_ticker": {},
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass
