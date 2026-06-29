import base64
import io

import numpy as np
from fastapi import APIRouter, Depends
from PIL import Image as PILImage
from typing_extensions import TypedDict

from facefinder.api.deps import identify_service
from facefinder.services.identify import IdentifyService

router = APIRouter(prefix="/identify", tags=["identify"])


class IdentifyBody(TypedDict):
    embedding: list[float]


class IdentifyImageBody(TypedDict):
    image_data: str


class CandidateDict(TypedDict):
    person_id: int | None
    similarity: float
    band: str


class IdentifyResponse(TypedDict):
    candidates: list[CandidateDict]


@router.post("")
async def route_identify(
    body: IdentifyBody | IdentifyImageBody,
    svc: IdentifyService = Depends(identify_service),
) -> object:
    if "image_data" in body:
        data = base64.b64decode(body["image_data"])
        img = PILImage.open(io.BytesIO(data)).convert("RGB")
        return svc.identify_from_image(np.array(img))

    candidates = svc.identify(body["embedding"])
    return {
        "candidates": [
            {"person_id": c.person_id, "similarity": c.similarity, "band": c.band}
            for c in candidates
        ]
    }
