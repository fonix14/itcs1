from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from app.auth import make_password_pair
from app.db import SessionLocal


async def main():
    if len(sys.argv) != 3:
        print("usage: python -m app.scripts.set_user_password <email> <password>")
        raise SystemExit(1)

    email = sys.argv[1].strip()
    password = sys.argv[2]

    salt, password_hash = make_password_pair(password)

    async with SessionLocal() as session:
        try:
            await session.execute(
                text(
                    """
                    update users
                    set password_salt = :salt,
                        password_hash = :password_hash
                    where lower(email) = lower(:email)
                    """
                ),
                {
                    "email": email,
                    "salt": salt,
                    "password_hash": password_hash,
                },
            )
            await session.commit()
            print("ok")
        except Exception as e:
            await session.rollback()
            print(f"error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
