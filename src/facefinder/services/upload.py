import io
from datetime import UTC, datetime
from typing import TypedDict

import numpy as np
from PIL import Image as PILImage

from facefinder.constants.enums import StorageKind
from facefinder.constants.types import DetectedFace, FaceData, ImageData
from facefinder.data import Faces, Images
from facefinder.data.storage import crop, open_bytes, sha256_bytes
from facefinder.data.storage import put as storage_put
from facefinder.domains.recognition.dedup import CandidateMatch
from facefinder.domains.recognition.engine import detect_and_embed
from facefinder.services.base import BaseService
from facefinder.services.identify import IdentifyService

__all__ = ["ProcessResult", "StoreResult", "UploadService"]


class StoreResult(TypedDict):
    status: str  # "created" | "duplicate"
    image: ImageData | None


class ProcessResult(TypedDict):
    image: ImageData | None
    faces: list[FaceData]
    candidates: list[list[CandidateMatch]]


def _save_crop(pil: PILImage.Image, bbox: list[int]) -> str:
    buf = io.BytesIO()
    crop(pil, bbox).save(buf, format="JPEG")
    return storage_put(StorageKind.FACES, buf.getvalue(), "jpg")


def _exif(data: bytes) -> dict[str, object]:
    try:
        img = PILImage.open(io.BytesIO(data))
        exif = img.getexif()
        if exif:
            result: dict[str, object] = {str(k): str(v) for k, v in exif.items() if v is not None}
            return result
    except Exception:
        pass
    return {}


class UploadService(BaseService):
    def store(
        self,
        data: bytes,
        filename: str = "unknown.jpg",
        source: str = "",
        force: bool = False,
    ) -> StoreResult:
        """Step 1: persist the image bytes only. No face detection yet —
        processed_at stays NULL until process() runs. force=True skips the
        sha256 dedup check so a byte-identical image can be stored as new."""
        h = sha256_bytes(data)

        if not force:
            existing = Images.by_hash(h)
            if existing:
                return {"status": "duplicate", "image": existing}

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
        path = storage_put(StorageKind.IMAGES, data, ext=ext)
        meta = _exif(data)
        image = Images.create(
            sha256=h, path=path, format=ext, source=source, uploaded_by=self.actor_id, meta=meta
        )
        return {"status": "created", "image": image}

    def process(self, image_id: int) -> ProcessResult | None:
        """Step 2: detect + embed faces, save crops, mark the image processed,
        and return per-face match candidates for review. Idempotent — re-running
        on an already-processed image returns its existing faces, not new rows."""
        image = Images.get(image_id)
        if image is None:
            return None

        if image.processed_at is not None:
            faces = Faces.for_image(image_id)
        else:
            data = open_bytes(StorageKind.IMAGES, image.path)
            pil = PILImage.open(io.BytesIO(data)).convert("RGB")
            detected: list[DetectedFace] = detect_and_embed(np.array(pil))
            crop_paths = [_save_crop(pil, f["bbox"]) for f in detected]
            faces = Faces.bulk_create(image_id, detected, crop_paths)
            image = Images.update(image_id, processed_at=datetime.now(UTC)) or image

        identifier = IdentifyService(self.actor)
        candidates = [identifier.identify(f.embedding, exclude_face_id=f.id) for f in faces]
        return {"image": image, "faces": faces, "candidates": candidates}

    # Read-only accessors so API routers stay a shell over services.
    def list_images(
        self, limit: int = 24, offset: int = 0, processed: bool | None = None
    ) -> tuple[list[ImageData], int]:
        return Images.page(limit=limit, offset=offset, processed=processed)

    def get_image(self, image_id: int) -> ImageData | None:
        return Images.get(image_id)

    def image_bytes(self, image_id: int) -> tuple[bytes, str] | None:
        """Raw image bytes + format, or None if the image is gone."""
        image = Images.get(image_id)
        if image is None:
            return None
        return open_bytes(StorageKind.IMAGES, image.path), image.format or "jpeg"
