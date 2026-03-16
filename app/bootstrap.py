from __future__ import annotations

import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import make_password_pair


async def ensure_bootstrap_admin(session: AsyncSession) -> None:
    email = (os.getenv("BOOTSTRAP_ADMIN_EMAIL") or "admin@local").strip().lower()
    password = (os.getenv("BOOTSTRAP_ADMIN_PASSWORD") or "Admin12345!").strip()
    full_name = (os.getenv("BOOTSTRAP_ADMIN_FULL_NAME") or "System Admin").strip()

    if not email or not password:
        return

    try:
        res = await session.execute(
            text(
                """
                select id::text as id, email, role
                from users
                where lower(email) = lower(:email)
                limit 1
                """
            ),
            {"email": email},
        )
        row = res.mappings().first()

        salt, password_hash = make_password_pair(password)

        if row:
            await session.execute(
                text(
                    """
                    update users
                    set
                        full_name = coalesce(nullif(full_name, ''), :full_name),
                        role = case when role in ('admin', 'dispatcher') then role else 'admin' end,
                        is_active = true,
                        password_salt = :salt,
                        password_hash = :password_hash
                    where lower(email) = lower(:email)
                    """
                ),
                {
                    "email": email,
                    "full_name": full_name,
                    "salt": salt,
                    "password_hash": password_hash,
                },
            )
        else:
            await session.execute(
                text(
                    """
                    insert into users (
                        id,
                        full_name,
                        email,
                        role,
                        is_active,
                        password_salt,
                        password_hash
                    )
                    values (
                        gen_random_uuid(),
                        :full_name,
                        :email,
                        'admin',
                        true,
                        :salt,
                        :password_hash
                    )
                    """
                ),
                {
                    "full_name": full_name,
                    "email": email,
                    "salt": salt,
                    "password_hash": password_hash,
                },
            )

        await session.commit()
    except Exception:
        await session.rollback()
        raise
