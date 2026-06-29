from fastapi import APIRouter
from typing_extensions import TypedDict

from facefinder.data import Faces, Images, Persons

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class RecentImage(TypedDict):
    id: int | None
    format: str
    source: str
    processed: bool
    uploaded_at: str


class DashboardResponse(TypedDict):
    images: dict[str, int]  # total, processed, unprocessed
    faces_unassigned: int
    people: int
    recent: list[RecentImage]


@router.get("")
def route_dashboard() -> DashboardResponse:
    return {
        "images": Images.stats(),
        "faces_unassigned": Faces.count_unidentified(),
        # ponytail: counting via list() is fine at this scale; add a COUNT query
        # if the person table ever grows past a few thousand rows.
        "people": len(Persons.all()),
        "recent": [
            {
                "id": img.id,
                "format": img.format,
                "source": img.source,
                "processed": img.processed_at is not None,
                "uploaded_at": str(img.uploaded_at),
            }
            for img in Images.recent()
        ],
    }
