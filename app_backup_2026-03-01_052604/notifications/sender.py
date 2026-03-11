from __future__ import annotations

import json
from typing import Any

from pywebpush import webpush, WebPushException
import aiosmtplib
from email.message import EmailMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DeviceSubscription
from app.settings import settings


async def send_web_push(db: AsyncSession, user_id: str, payload: dict[str, Any]) -> tuple[bool, str | None]:
    if not settings.vapid_private_key or not settings.vapid_public_key:
        return False, "vapid_not_configured"

    res = await db.execute(
        select(DeviceSubscription)
        .where(DeviceSubscription.user_id == user_id)
        .where(DeviceSubscription.is_active == True)
    )
    subs = res.scalars().all()
    if not subs:
        return False, "no_subscription"

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    last_err = None
    sent_any = False
    for s in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": s.endpoint,
                    "keys": {"p256dh": s.p256dh, "auth": s.auth},
                },
                data=data,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
            )
            sent_any = True
        except WebPushException as e:
            last_err = f"webpush_error: {str(e)}"
            try:
                code = getattr(e.response, "status_code", None)
                if code in (404, 410):
                    s.is_active = False
            except Exception:
                pass
        except Exception as e:
            last_err = f"webpush_exception: {type(e).__name__}: {e}"
    return sent_any, last_err


async def send_email(to_email: str, subject: str, body: str) -> tuple[bool, str | None]:
    if not settings.smtp_host:
        return False, "smtp_not_configured"

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        client = aiosmtplib.SMTP(hostname=settings.smtp_host, port=settings.smtp_port, start_tls=settings.smtp_tls)
        await client.connect()
        if settings.smtp_user:
            await client.login(settings.smtp_user, settings.smtp_pass)
        await client.send_message(msg)
        await client.quit()
        return True, None
    except Exception as e:
        return False, f"smtp_exception: {type(e).__name__}: {e}"
