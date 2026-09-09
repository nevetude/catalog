"""Auth API: register, login, logout, current user."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth import create_session, current_user, hash_password, verify_password
from app.config import COOKIE, SESSION_MAX_AGE
from app.db import ensure_folders, get_db

router = APIRouter(prefix="/api", tags=["auth"])


class Credentials(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=2, max_length=200)


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=SESSION_MAX_AGE)


@router.get("/me")
def me(request: Request):
    user = current_user(request)
    return {"authenticated": bool(user), "user": user}


@router.post("/auth/register")
def register(body: Credentials, response: Response):
    username = body.username.strip()
    with get_db() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(body.password)),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(400, "username taken")
        user_id = cursor.lastrowid
        ensure_folders(conn, user_id)
        token = create_session(conn, user_id)
    _set_cookie(response, token)
    return {"ok": True, "user": {"id": user_id, "username": username}}


@router.post("/auth/login")
def login(body: Credentials, response: Response):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (body.username.strip(),)
        ).fetchone()
        if not row or not verify_password(body.password, row["password_hash"]):
            raise HTTPException(401, "invalid credentials")
        if not row["password_hash"].startswith("pbkdf2$"):
            # Transparently upgrade hashes created by versions before 5.0.
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(body.password), row["id"]),
            )
        ensure_folders(conn, row["id"])
        token = create_session(conn, row["id"])
    _set_cookie(response, token)
    return {"ok": True, "user": {"id": row["id"], "username": row["username"]}}


@router.post("/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        with get_db() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    response.delete_cookie(COOKIE)
    return {"ok": True}
