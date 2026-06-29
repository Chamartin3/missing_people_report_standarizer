from facefinder.constants.enums import StorageKind
from facefinder.data import Images
from facefinder.data.storage import open_bytes
from facefinder.domains.ocr import extract_text
from facefinder.services.base import BaseService

__all__ = ["OcrService"]


class OcrService(BaseService):
    def text_for_image(self, image_id: int) -> str | None:
        """OCR text for a stored image, or None if the image doesn't exist."""
        image = Images.get(image_id)
        if image is None:
            return None
        return extract_text(open_bytes(StorageKind.IMAGES, image.path))
