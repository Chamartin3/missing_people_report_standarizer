import io
import os

import pytesseract
from PIL import Image as PILImage

# Documents here are mostly Spanish (cédulas, etc.); the English model mangles
# accents/ñ and Spanish words. Override with OCR_LANG (e.g. "spa", "eng").
_LANG = os.getenv("OCR_LANG", "spa+eng")


def extract_text(image_bytes: bytes) -> str:
    """OCR an image to plain text.

    Shells out to the `tesseract` binary (with the `spa` + `eng` language packs),
    baked into the Docker image — see Dockerfile; no host install needed via compose.
    """
    # pytesseract is untyped; with the default output type it returns a str.
    text = pytesseract.image_to_string(  # type: ignore
        PILImage.open(io.BytesIO(image_bytes)), lang=_LANG
    )
    return str(text).strip()
