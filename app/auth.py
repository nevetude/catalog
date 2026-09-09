"""Password hashing, sessions and request dependencies."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from typing import Optional

from fastapi import HTTPException, Request

from app.config import COOKIE
from app.db import get_db

PBKDF2_ITERATIONS = 240_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify pbkdf2 hashes; also accepts the legacy salted-sha256 format."""
    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == "pbkdf2":
        _, iterations, salt, digest = parts
        check = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        )
        return secrets.compare_digest(check.hex(), digest)
    if len(parts) == 2:  # legacy: salt$sha256(salt + password)
        salt, digest = parts
        check = hashlib.sha256((salt + password).encode()).hexdigest()
        return secrets.compare_digest(check, digest)
    return False


def create_session(conn: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_hex(32)
    conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    return token


def current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT u.id, u.username FROM sessions s "
            "JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (token,),
        ).fetchone()
    return dict(row) if row else None


def require_user(request: Request) -> dict:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="unauthorized")
    return user
