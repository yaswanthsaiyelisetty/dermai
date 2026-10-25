from datetime import datetime

from fastapi import HTTPException
from pydantic import BaseModel, Field

from backend.app.database import get_db_connection

ALLOWED_STATUSES = {"open", "in_progress", "closed"}


class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    status: str = "open"


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = None


def initialize_case_tables() -> None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(120) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'in_progress', 'closed')),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS cases_user_id_idx ON cases(user_id)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS case_images (
                    id BIGSERIAL PRIMARY KEY,
                    case_id BIGINT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                    filename VARCHAR(255) NOT NULL,
                    format VARCHAR(10) NOT NULL,
                    width INTEGER NOT NULL CHECK (width > 0),
                    height INTEGER NOT NULL CHECK (height > 0),
                    size_bytes INTEGER NOT NULL CHECK (size_bytes > 0),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


def _validate_status(status: str | None) -> None:
    if status is not None and status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=422,
            detail="status must be open, in_progress, or closed",
        )


def _serialize_case(row: tuple) -> dict:
    return {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "status": row[3],
        "created_at": row[4].isoformat(),
        "updated_at": row[5].isoformat(),
        "images": row[6],
    }


def create_case(user_id: int, request: CaseCreate) -> dict:
    _validate_status(request.status)
    initialize_case_tables()
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO cases (user_id, title, description, status)
                VALUES (%s, %s, %s, %s)
                RETURNING id, title, description, status, created_at, updated_at
                """,
                (user_id, request.title.strip(), request.description, request.status),
            )
            row = cursor.fetchone()
    return _serialize_case((*row, []))


def list_cases(user_id: int) -> list[dict]:
    initialize_case_tables()
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.id, c.title, c.description, c.status,
                       c.created_at, c.updated_at, COUNT(ci.id)
                FROM cases c
                LEFT JOIN case_images ci ON ci.case_id = c.id
                WHERE c.user_id = %s
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
    return [_serialize_case(row) for row in rows]


def get_case(user_id: int, case_id: int) -> dict:
    initialize_case_tables()
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.id, c.title, c.description, c.status,
                       c.created_at, c.updated_at,
                       COALESCE(
                           json_agg(json_build_object(
                               'id', ci.id, 'filename', ci.filename,
                               'format', ci.format, 'width', ci.width,
                               'height', ci.height, 'size_bytes', ci.size_bytes,
                               'created_at', ci.created_at
                           ) ORDER BY ci.created_at DESC)
                           FILTER (WHERE ci.id IS NOT NULL), '[]'
                       )
                FROM cases c
                LEFT JOIN case_images ci ON ci.case_id = c.id
                WHERE c.id = %s AND c.user_id = %s
                GROUP BY c.id
                """,
                (case_id, user_id),
            )
            row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return _serialize_case(row)


def update_case(user_id: int, case_id: int, request: CaseUpdate) -> dict:
    _validate_status(request.status)
    initialize_case_tables()
    values = request.model_dump(exclude_unset=True)
    if "title" in values:
        values["title"] = values["title"].strip()
    if not values:
        return get_case(user_id, case_id)

    assignments = ", ".join(f"{field} = %s" for field in values)
    parameters = list(values.values()) + [datetime.now().astimezone(), case_id, user_id]
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE cases
                SET {assignments}, updated_at = %s
                WHERE id = %s AND user_id = %s
                """,
                parameters,
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Case not found")
    return get_case(user_id, case_id)


def delete_case(user_id: int, case_id: int) -> None:
    initialize_case_tables()
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM cases WHERE id = %s AND user_id = %s",
                (case_id, user_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Case not found")


def attach_image(user_id: int, case_id: int, image: dict) -> None:
    initialize_case_tables()
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO case_images
                    (case_id, filename, format, width, height, size_bytes)
                SELECT id, %s, %s, %s, %s, %s
                FROM cases
                WHERE id = %s AND user_id = %s
                RETURNING id
                """,
                (
                    image["filename"],
                    image["format"],
                    image["width"],
                    image["height"],
                    image["size_bytes"],
                    case_id,
                    user_id,
                ),
            )
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Case not found")
