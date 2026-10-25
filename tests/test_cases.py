import os
import uuid
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.database import get_db_connection
from backend.app.main import app

os.environ.setdefault("AUTH_SECRET", "test-only-auth-secret")


def test_case_endpoints_enforce_user_ownership():
    username_a = f"case_a_{uuid.uuid4().hex[:10]}"
    username_b = f"case_b_{uuid.uuid4().hex[:10]}"
    password = "test-password-123"
    created_case_id = None

    try:
        with TestClient(app) as client:
            register_a = client.post(
                "/auth/register",
                json={"username": username_a, "password": password},
            )
            register_b = client.post(
                "/auth/register",
                json={"username": username_b, "password": password},
            )
            assert register_a.status_code == 201
            assert register_b.status_code == 201

            login_a = client.post(
                "/auth/login",
                json={"username": username_a, "password": password},
            )
            login_b = client.post(
                "/auth/login",
                json={"username": username_b, "password": password},
            )
            token_a = login_a.json()["access_token"]
            token_b = login_b.json()["access_token"]

            assert client.get("/cases").status_code == 401
            created = client.post(
                "/cases",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"title": "Test case", "description": "Isolation test"},
            )
            assert created.status_code == 201
            created_case_id = created.json()["id"]

            listed = client.get(
                "/cases", headers={"Authorization": f"Bearer {token_a}"}
            )
            assert listed.status_code == 200
            assert [item["id"] for item in listed.json()] == [created_case_id]

            other_user_get = client.get(
                f"/cases/{created_case_id}",
                headers={"Authorization": f"Bearer {token_b}"},
            )
            other_user_update = client.patch(
                f"/cases/{created_case_id}",
                headers={"Authorization": f"Bearer {token_b}"},
                json={"status": "closed"},
            )
            assert other_user_get.status_code == 404
            assert other_user_update.status_code == 404

            updated = client.patch(
                f"/cases/{created_case_id}",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"status": "in_progress"},
            )
            assert updated.status_code == 200
            assert updated.json()["status"] == "in_progress"

            image_buffer = BytesIO()
            Image.new("RGB", (16, 16), color="red").save(image_buffer, format="PNG")
            image_buffer.seek(0)
            upload = client.post(
                f"/images/upload?case_id={created_case_id}",
                headers={"Authorization": f"Bearer {token_a}"},
                files={"file": ("case.png", image_buffer, "image/png")},
            )
            assert upload.status_code == 200
            case_with_image = client.get(
                f"/cases/{created_case_id}",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert case_with_image.status_code == 200
            assert len(case_with_image.json()["images"]) == 1
    finally:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                if created_case_id is not None:
                    cursor.execute("DELETE FROM cases WHERE id = %s", (created_case_id,))
                cursor.execute(
                    "DELETE FROM users WHERE username IN (%s, %s)",
                    (username_a, username_b),
                )
