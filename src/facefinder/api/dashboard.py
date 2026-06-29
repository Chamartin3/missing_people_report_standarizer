from fastapi import APIRouter, Depends
from typing_extensions import TypedDict

from facefinder.api.deps import casefile_service
from facefinder.services.casefile import CasefileService

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
def route_dashboard(
    svc: CasefileService = Depends(casefile_service),
) -> DashboardResponse:
    data = svc.dashboard()
    return {
        "images": data["images"],
        "faces_unassigned": data["faces_unassigned"],
        "people": data["people"],
        "recent": [
            {
                "id": img.id,
                "format": img.format,
                "source": img.source,
                "processed": img.processed_at is not None,
                "uploaded_at": str(img.uploaded_at),
            }
            for img in data["recent"]
        ],
    }
