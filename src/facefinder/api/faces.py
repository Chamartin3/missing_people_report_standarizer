from typing import NotRequired

from fastapi import APIRouter, Depends, HTTPException, Response
from typing_extensions import TypedDict

from facefinder.api.deps import identify_service
from facefinder.constants.enums import ConfirmationLevel, StorageKind
from facefinder.constants.types import FaceData
from facefinder.data import Faces, Persons
from facefinder.data.storage import open_bytes
from facefinder.services.identify import IdentifyService

router = APIRouter(prefix="/faces", tags=["faces"])

# Hide near-random neighbours from the "similar faces" panel — only surface hits
# the curator could plausibly act on.
SIMILAR_MIN = 0.40


class FaceDict(TypedDict):
    id: int | None
    image_id: int
    person_id: int | None
    confirmation: str
    det_score: float
    crop_url: str
    image_url: str


class FaceListResponse(TypedDict):
    faces: list[FaceDict]
    total: int
    unidentified: int


class SimilarFace(TypedDict):
    face_id: int
    image_id: int
    person_id: int | None
    display_name: str | None
    similarity: float
    crop_url: str


class FaceDetailResponse(TypedDict):
    face: FaceDict
    person: dict[str, object] | None
    similar: list[SimilarFace]


def _face_dict(f: FaceData) -> FaceDict:
    return {
        "id": f.id,
        "image_id": f.image_id,
        "person_id": f.person_id,
        "confirmation": f.confirmation,
        "det_score": f.det_score,
        "crop_url": f"/faces/{f.id}/crop",
        "image_url": f"/images/{f.image_id}/file",
    }


class AssignBody(TypedDict):
    person_id: NotRequired[int | None]
    level: NotRequired[str]
    confidence: NotRequired[float | None]


class SearchBody(TypedDict):
    embedding: list[float]


class AssignResponse(TypedDict):
    error: str


class AssignOkResponse(TypedDict):
    face_id: int | None
    person_id: int | None
    confirmation: ConfirmationLevel


class CandidateDict(TypedDict):
    person_id: int | None
    similarity: float
    distance: float
    band: str
    faces: list[int]


class SearchResponse(TypedDict):
    candidates: list[CandidateDict]


@router.get("")
def route_list(
    assigned: str = "all",
    person_id: int | None = None,
    confirmation: str | None = None,
    limit: int = 24,
    offset: int = 0,
    svc: IdentifyService = Depends(identify_service),
) -> FaceListResponse:
    # assigned: "all" | "yes" | "no". person_id, when given, overrides it.
    flag = {"yes": True, "no": False}.get(assigned)
    faces, total = Faces.page(
        assigned=flag,
        person_id=person_id,
        confirmation=confirmation or None,
        limit=limit,
        offset=offset,
    )
    return {
        "faces": [_face_dict(f) for f in faces],
        "total": total,
        "unidentified": Faces.count_unidentified(),
    }


@router.get("/{face_id}")
def route_get(
    face_id: int,
    svc: IdentifyService = Depends(identify_service),
) -> FaceDetailResponse:
    face = Faces.get(face_id)
    if face is None:
        raise HTTPException(status_code=404, detail="face not found")

    person = None
    if face.person_id is not None:
        p = Persons.get(face.person_id)
        if p is not None:
            person = {"id": p.id, "display_name": p.display_name, "status": p.status}

    # Similar faces are only useful while the face is still unassigned. Show only
    # real matches (>= SIMILAR_MIN) and collapse duplicates: one entry per person
    # (best match), and one per byte-identical crop (same image stored twice).
    similar: list[SimilarFace] = []
    if face.person_id is None:
        seen: set[object] = set()
        # over-fetch so threshold + dedup still leave a useful number.
        for hit in Faces.nearest(face.embedding, k=48, exclude_id=face_id):
            similarity = round(1.0 - hit.distance, 4)
            if similarity < SIMILAR_MIN:
                break  # ordered by similarity desc — nothing below will qualify
            key: object = (
                ("person", hit.person_id) if hit.person_id is not None else ("crop", hit.crop_path)
            )
            if key in seen:
                continue
            seen.add(key)
            named = Persons.get(hit.person_id) if hit.person_id is not None else None
            similar.append(
                {
                    "face_id": hit.id,
                    "image_id": hit.image_id,
                    "person_id": hit.person_id,
                    "display_name": named.display_name if named else None,
                    "similarity": similarity,
                    "crop_url": f"/faces/{hit.id}/crop",
                }
            )
            if len(similar) >= 12:
                break

    return {"face": _face_dict(face), "person": person, "similar": similar}


@router.get("/{face_id}/crop")
def route_crop(face_id: int) -> Response:
    face = Faces.get(face_id)
    if face is None or face.crop_path is None:
        raise HTTPException(status_code=404, detail="crop not found")
    return Response(open_bytes(StorageKind.FACES, face.crop_path), media_type="image/jpeg")


@router.post("/{face_id}/assign")
def route_assign(
    face_id: int,
    body: AssignBody,
    svc: IdentifyService = Depends(identify_service),
) -> AssignResponse | AssignOkResponse:
    level = ConfirmationLevel(body.get("level", ConfirmationLevel.SUGGESTED))
    result = svc.assign(
        face_id=face_id,
        person_id=body.get("person_id"),
        level=level,
        confidence=body.get("confidence"),
    )
    if result is None:
        return {"error": "face not found"}
    return {
        "face_id": result.id,
        "person_id": result.person_id,
        "confirmation": result.confirmation,
    }


@router.post("/search")
async def route_search(
    body: SearchBody,
    svc: IdentifyService = Depends(identify_service),
) -> SearchResponse:
    candidates = svc.identify(body["embedding"])
    return {
        "candidates": [
            {
                "person_id": c.person_id,
                "similarity": c.similarity,
                "distance": c.distance,
                "band": c.band,
                "faces": c.faces,
            }
            for c in candidates
        ]
    }
