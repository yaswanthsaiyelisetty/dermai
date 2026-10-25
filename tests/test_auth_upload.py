from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.auth import hash_password, verify_password
from backend.app.main import app


def test_password_hash_is_not_plaintext():
    password = "safe-password-123"
    stored_hash = hash_password(password)

    assert stored_hash != password
    assert verify_password(password, stored_hash)
    assert not verify_password("wrong-password", stored_hash)


def test_upload_accepts_valid_png():
    image_buffer = BytesIO()
    Image.new("RGB", (32, 24), color="red").save(image_buffer, format="PNG")
    image_buffer.seek(0)

    with TestClient(app) as client:
        response = client.post(
            "/images/upload",
            files={"file": ("skin.png", image_buffer, "image/png")},
        )

    assert response.status_code == 200
    assert response.json()["image"]["format"] == "PNG"


def test_upload_rejects_invalid_image():
    with TestClient(app) as client:
        response = client.post(
            "/images/upload",
            files={"file": ("skin.png", b"not an image", "image/png")},
        )

    assert response.status_code == 400
