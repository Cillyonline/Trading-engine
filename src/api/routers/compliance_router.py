"""Compliance control endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from cilly_trading.compliance.daily_loss_guard import acknowledge_daily_loss_breach


def build_compliance_router() -> APIRouter:
    router = APIRouter(prefix="/compliance", tags=["compliance"])

    @router.post(
        "/daily-loss/acknowledge",
        summary="Acknowledge daily loss breach",
        description=(
            "Clears the awaiting_acknowledgment flag set by the require_acknowledgment "
            "breach-action policy. After this call, execution resumes on the next guard "
            "check. If the portfolio still exceeds the loss limit, the guard triggers again."
        ),
    )
    def acknowledge_daily_loss_handler() -> dict[str, str]:
        acknowledge_daily_loss_breach()
        return {"status": "acknowledged"}

    return router
