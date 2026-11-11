import asyncio
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import Settings, get_settings

MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_FORMATS = {
    "jpeg": ".jpg",
    "png": ".png",
    "webp": ".webp",
    "gif": ".gif",
}


def detect_image_format(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff") and b"\xff\xd9" in data[3:]:
        return "jpeg"
    if (
        data.startswith(b"\x89PNG\r\n\x1a\n")
        and len(data) >= 33
        and data[12:16] == b"IHDR"
        and b"\x00\x00\x00\x00IEND\xaeB`\x82" in data[8:]
    ):
        return "png"
    if data.startswith((b"GIF87a", b"GIF89a")) and b";" in data[6:]:
        return "gif"
    if (
        data.startswith(b"RIFF")
        and data[8:12] == b"WEBP"
        and int.from_bytes(data[4:8], "little") + 8 <= len(data)
    ):
        return "webp"
    return None


class ImageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def upload(self, file: UploadFile) -> str:
        data = await file.read(MAX_IMAGE_BYTES + 1)
        await file.close()
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Image file exceeds 10 MB",
            )
        image_format = detect_image_format(data)
        if image_format is None:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Uploaded file is not a supported image",
            )

        filename = f"{secrets.token_hex(16)}{IMAGE_FORMATS[image_format]}"
        destination = self._destination(filename)
        await asyncio.to_thread(destination.write_bytes, data)
        return f"/media/images/{filename}"

    def _destination(self, filename: str) -> Path:
        directory = (Path(self.settings.upload_dir).resolve() / "images").resolve()
        directory.mkdir(parents=True, exist_ok=True)
        destination = (directory / filename).resolve()
        if destination.parent != directory:
            raise ValueError("Invalid image path")
        return destination
