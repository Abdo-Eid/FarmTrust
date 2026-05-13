"""Evidence aggregation helpers."""

from __future__ import annotations

from typing import Any


def build_risk_flag(code: str, severity: str, reason: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": severity,
        "reason": reason,
    }


def build_confidence_payload(level: str, reasons: list[str]) -> dict[str, Any]:
    return {
        "level": level,
        "reasons": reasons,
    }
