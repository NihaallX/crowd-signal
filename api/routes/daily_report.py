"""Daily report routes for morning catalyst summary."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException

from engine.scanner.catalyst_scanner import get_todays_report, run_daily_scan

router = APIRouter()


@router.get("/daily-report")
async def daily_report() -> dict[str, Any]:
    report = get_todays_report()
    if report is None:
        return {
            "status": "generating",
            "message": "Report not ready yet",
            "us_entries": [],
            "in_entries": [],
        }

    payload = dict(report)
    payload["status"] = "ready"
    return payload


@router.post("/daily-report/trigger")
async def trigger_daily_report(x_admin_key: str | None = Header(default=None)) -> dict[str, Any]:
    admin_key = os.getenv("ADMIN_KEY")
    if not admin_key or (x_admin_key or "") != admin_key:
        raise HTTPException(status_code=403, detail="Unauthorized")

    return await run_daily_scan("ALL")
