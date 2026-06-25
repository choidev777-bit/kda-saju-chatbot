"""Small display helpers for profile and tool result data."""

from __future__ import annotations

from src import config


def profile_summary(profile: dict | None) -> dict:
    if not profile or not profile.get("ok"):
        return {"ready": False, "name": None, "pillars": [], "elements": None, "pending_tools": []}

    data = profile.get("data") or {}
    user = data.get("user") or {}
    saju = data.get("saju_chart") or {}
    five = data.get("five_elements") or {}
    pillars = [
        ("연주", saju.get("year_pillar")),
        ("월주", saju.get("month_pillar")),
        ("일주", saju.get("day_pillar")),
        ("시주", saju.get("hour_pillar") or "모름"),
    ]

    elements = None
    counts = five.get("counts") if isinstance(five, dict) else None
    if counts:
        elements = ", ".join(
            f"{config.ELEMENT_KO.get(key, key)} {counts.get(key, 0)}"
            for key in config.ELEMENTS
        )

    return {
        "ready": True,
        "name": user.get("name") or "사용자",
        "pillars": pillars,
        "elements": elements,
        "pending_tools": data.get("pending_tools") or [],
    }


def pending_tools_text(pending_tools: list[str] | tuple[str, ...] | None) -> str | None:
    if not pending_tools:
        return None
    return "아직 준비 중인 기능: " + ", ".join(str(tool) for tool in pending_tools)
