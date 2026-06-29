from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from typing_extensions import TypedDict

from facefinder.api.deps import ocr_service, upload_service
from facefinder.services.ocr import OcrService
from facefinder.services.upload import UploadService

router = APIRouter(prefix="/images", tags=["images"])


class CandidateDict(TypedDict):
    person_id: int | None
    display_name: str | None
    similarity: float
    band: str
    faces: list[int]


class UploadedFace(TypedDict):
    face_id: int | None
    bbox: list[int]
    crop_url: str
    candidates: list[CandidateDict]


class StoreResponse(TypedDict):
    status: str  # "created" | "duplicate"
    image_id: int | None
    processed: bool


class ProcessResponse(TypedDict):
    image_id: int | None
    faces: list[UploadedFace]


class ImageItem(TypedDict):
    id: int | None
    source: str
    format: str
    uploaded_at: str
    processed: bool
    file_url: str


class ImageListResponse(TypedDict):
    images: list[ImageItem]
    total: int


@router.get("")
def route_list(
    limit: int = 24,
    offset: int = 0,
    processed: bool | None = None,
    svc: UploadService = Depends(upload_service),
) -> ImageListResponse:
    images, total = svc.list_images(limit=limit, offset=offset, processed=processed)
    return {
        "images": [
            {
                "id": img.id,
                "source": img.source,
                "format": img.format,
                "uploaded_at": str(img.uploaded_at),
                "processed": img.processed_at is not None,
                "file_url": f"/images/{img.id}/file",
            }
            for img in images
        ],
        "total": total,
    }


@router.post("")
async def route_upload(
    file: Annotated[UploadFile, File(...)],
    source: Annotated[str, Form()] = "",
    force: Annotated[bool, Form()] = False,
    svc: UploadService = Depends(upload_service),
) -> StoreResponse:
    """Step 1: store the image. Detection happens later via /images/{id}/process.
    force=True stores even a byte-identical duplicate as a new image."""
    data = await file.read()
    result = svc.store(data, filename=file.filename or "unknown.jpg", source=source, force=force)
    image = result["image"]
    return {
        "status": result["status"],
        "image_id": image.id if image is not None else None,
        "processed": image.processed_at is not None if image is not None else False,
    }


@router.post("/{image_id}/process")
def route_process(
    image_id: int,
    svc: UploadService = Depends(upload_service),
) -> ProcessResponse:
    """Step 2: detect faces + return per-face match candidates for review."""
    result = svc.process(image_id)
    if result is None:
        raise HTTPException(status_code=404, detail="image not found")
    # candidates[i] are the similar faces for faces[i] — surface both so the UI
    # can show the duplicate banner and offer assign-to-existing-person.
    faces: list[UploadedFace] = [
        {
            "face_id": f.id,
            "bbox": f.bbox,
            "crop_url": f"/faces/{f.id}/crop",
            "candidates": [
                {
                    "person_id": c.person_id,
                    "display_name": c.display_name,
                    "similarity": c.similarity,
                    "band": c.band,
                    "faces": c.faces,
                }
                for c in cands
            ],
        }
        for f, cands in zip(result["faces"], result["candidates"], strict=True)
    ]
    return {
        "image_id": image_id,
        "faces": faces,
    }


@router.get("/{image_id}/file")
def route_image_file(
    image_id: int,
    svc: UploadService = Depends(upload_service),
) -> Response:
    result = svc.image_bytes(image_id)
    if result is None:
        raise HTTPException(status_code=404, detail="image not found")
    data, fmt = result
    return Response(data, media_type=f"image/{fmt}")


class OcrResponse(TypedDict):
    text: str


@router.get("/{image_id}/text")
def route_image_text(
    image_id: int,
    svc: OcrService = Depends(ocr_service),
) -> OcrResponse:
    text = svc.text_for_image(image_id)
    if text is None:
        raise HTTPException(status_code=404, detail="image not found")
    return {"text": text}
