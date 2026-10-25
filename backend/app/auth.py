import base64
import binascii
import hashlib
import hmac
import os
import secrets

from fastapi import Header, HTTPException
from pydantic import BaseModel, Field

from backend.app.database import get_db_connection


class RegistrationRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )
    return "scrypt${}${}".format(
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, encoded_salt, encoded_digest = stored_hash.split("$", 2)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
        actual_digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
        )
        return hmac.compare_digest(actual_digest, expected_digest)
    except (ValueError, TypeError):
        return False


def initialize_auth_table() -> None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


def register_user(request: RegistrationRequest) -> dict[str, str | int]:
    password_hash = hash_password(request.password)
    try:
        initialize_auth_table()
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (username, password_hash)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (request.username, password_hash),
                )
                user_id = cursor.fetchone()[0]
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Username already exists") from exc
        raise HTTPException(status_code=503, detail="Could not create user") from exc

    return {"id": user_id, "username": request.username}


def login_user(request: LoginRequest) -> dict[str, str]:
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT password_hash FROM users WHERE username = %s",
                    (request.username,),
                )
                row = cursor.fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not authenticate user") from exc

    if row is None or not verify_password(request.password, row[0]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    secret = os.getenv("AUTH_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="Authentication secret is not configured")

    payload = f"{request.username}:{secrets.token_urlsafe(24)}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    token = f"{base64.urlsafe_b64encode(payload).decode('ascii')}.{signature}"
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, int | str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization[7:]
    try:
        encoded_payload, signature = token.split(".", 1)
        payload = base64.urlsafe_b64decode(encoded_payload.encode("ascii"))
        username, _nonce = payload.decode("utf-8").split(":", 1)
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    secret = os.getenv("AUTH_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="Authentication secret is not configured")

    expected_signature = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, username FROM users WHERE username = %s",
                    (username,),
                )
                row = cursor.fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not verify authentication") from exc

    if row is None:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return {"id": row[0], "username": row[1]}


def get_optional_current_user(
    authorization: str | None = Header(default=None),
) -> dict[str, int | str] | None:
    if authorization is None:
        return None
    return get_current_user(authorization)
