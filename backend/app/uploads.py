from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}


async def validate_image_upload(file: UploadFile) -> dict[str, str | int]:
    filename = file.filename or ""
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Only JPG, JPEG, and PNG images are supported",
        )

    contents = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Image exceeds the 10 MB size limit")

    try:
        with Image.open(BytesIO(contents)) as image:
            image.verify()
        with Image.open(BytesIO(contents)) as image:
            width, height = image.size
            image_format = image.format or extension.lstrip(".").upper()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a readable image") from exc

    return {
        "filename": filename,
        "format": image_format,
        "width": width,
        "height": height,
        "size_bytes": len(contents),
    }
