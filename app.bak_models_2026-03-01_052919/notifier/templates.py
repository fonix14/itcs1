from __future__ import annotations

from typing import Any


def render_digest_after_upload(payload: dict[str, Any]) -> str:
    created = payload.get('created', 0)
    updated = payload.get('updated', 0)
    anomalies = payload.get('anomalies', 0)
    trust = payload.get('trust_level', 'GREEN')
    reasons = payload.get('reasons') or []
    url = payload.get('url') or ''

    lines = [
        "ITCS — импорт завершён",
        "",
        f"Новых: {created} / Изменилось: {updated}",
        f"Аномалии: {anomalies}",
    ]

    if trust and trust != 'GREEN':
        reason_txt = ", ".join(reasons) if reasons else "-"
        lines.append(f"Trust: {trust} ({reason_txt})")
    else:
        lines.append("Trust: GREEN")

    if url:
        lines.extend(["", url])

    return "\n".join(lines)


def render_daily_health(payload: dict[str, Any]) -> str:
    trust = payload.get('trust_level', 'GREEN')
    reasons = payload.get('reasons') or []
    no_import_hours = payload.get('no_import_hours')
    pending = payload.get('pending_anomalies')
    url = payload.get('url') or ''

    lines = [
        "ITCS — ежедневный health",
        "",
        f"Trust: {trust}",
        f"Причины: {', '.join(reasons) if reasons else '-'}",
    ]

    if no_import_hours is not None:
        lines.append(f"No import: {no_import_hours}h")
    if pending is not None:
        lines.append(f"Pending anomalies: {pending}")

    if url:
        lines.extend(["", url])

    return "\n".join(lines)
