"""Reset admin password script - run inside backend container"""
import asyncio
from app.core.database import engine
from app.core.security import hash_password
from sqlalchemy import text

async def reset_admin():
    pw_hash = hash_password("admin123")
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT count(*) FROM users WHERE username='admin'"))
        count = result.scalar()
        if count == 0:
            await conn.execute(
                text("INSERT INTO users (username, password_hash, full_name, is_admin) VALUES ('admin', :h, 'Administrator', TRUE)"),
                {"h": pw_hash}
            )
            print(f"Created admin user")
        else:
            await conn.execute(
                text("UPDATE users SET password_hash = :h WHERE username = 'admin'"),
                {"h": pw_hash}
            )
            print(f"Updated admin password")

asyncio.run(reset_admin())
