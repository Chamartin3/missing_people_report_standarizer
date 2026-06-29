from typing import NotRequired

from fastapi import APIRouter, Depends
from typing_extensions import TypedDict

from facefinder.api.deps import casefile_service, identify_service
from facefinder.constants.enums import ConfirmationLevel, PersonStatus, ReportKind
from facefinder.constants.types import PersonData
from facefinder.services.casefile import CasefileService
from facefinder.services.identify import IdentifyService

router = APIRouter(prefix="/persons", tags=["persons"])


class PersonDict(TypedDict):
    id: int | None
    display_name: str | None
    first_name: str | None
    last_name: str | None
    expected_location: str | None
    current_location: str | None
    last_seen: str | None
    cedula: str | None
    is_minor: bool
    notas: str
    status: str
    attributes: dict[str, object]
    created_at: str | None
    deleted_at: str | None


class FaceDict(TypedDict):
    id: int | None
    image_id: int
    person_id: int | None
    confirmation: str
    det_score: float


class ReportDict(TypedDict):
    id: int | None
    kind: str
    location: str
    notes: str
    reporter: int | None
    created_at: str | None


class CommentDict(TypedDict):
    id: int | None
    author: int
    body: str
    created_at: str | None


class PersonResponse(TypedDict):
    person: PersonDict
    faces: list[FaceDict]
    reports: list[ReportDict]
    comments: list[CommentDict]


class PersonListResponse(TypedDict):
    persons: list[PersonDict]


class ErrorResponse(TypedDict):
    error: str


def _person_dict(p: PersonData) -> PersonDict:
    return {
        "id": p.id,
        "display_name": p.display_name,
        "first_name": p.first_name,
        "last_name": p.last_name,
        "expected_location": p.expected_location,
        "current_location": p.current_location,
        "last_seen": p.last_seen,
        "cedula": p.cedula,
        "is_minor": p.is_minor,
        "notas": p.notas,
        "status": p.status,
        "attributes": p.attributes,
        "created_at": str(p.created_at) if p.created_at else None,
        "deleted_at": str(p.deleted_at) if p.deleted_at else None,
    }


class PersonOnlyResponse(TypedDict):
    person: PersonDict


class ReportIdResponse(TypedDict):
    report_id: int | None


class CommentIdResponse(TypedDict):
    comment_id: int | None


class ArchiveResponse(TypedDict):
    archived: bool
    person_id: int


class MergeResponse(TypedDict):
    merged: bool
    survivor_id: int


class UpdateBody(TypedDict):
    display_name: NotRequired[str | None]
    first_name: NotRequired[str | None]
    last_name: NotRequired[str | None]
    expected_location: NotRequired[str | None]
    current_location: NotRequired[str | None]
    last_seen: NotRequired[str | None]
    cedula: NotRequired[str | None]
    notas: NotRequired[str]
    is_minor: NotRequired[bool]
    status: NotRequired[str]


class ReportBody(TypedDict):
    kind: NotRequired[str]
    location: NotRequired[str]
    seen_at: NotRequired[str | None]
    notes: NotRequired[str]
    image_id: NotRequired[int | None]


class CommentBody(TypedDict):
    body: str


class MergeBody(TypedDict):
    survivor_id: int
    loser_id: int


class CreateAssignBody(TypedDict):
    face_id: int
    display_name: NotRequired[str | None]
    attributes: NotRequired[dict[str, object] | None]
    level: NotRequired[str]


class CreateAssignResponse(TypedDict):
    person_id: int | None
    face_id: int | None


class CreateBody(TypedDict):
    display_name: NotRequired[str | None]
    first_name: NotRequired[str | None]
    last_name: NotRequired[str | None]
    expected_location: NotRequired[str | None]
    current_location: NotRequired[str | None]
    last_seen: NotRequired[str | None]
    cedula: NotRequired[str | None]
    notas: NotRequired[str]
    is_minor: NotRequired[bool]
    status: NotRequired[str]


@router.get("")
def route_list(
    svc: CasefileService = Depends(casefile_service),
) -> PersonListResponse:
    return {"persons": [_person_dict(p) for p in svc.list_persons()]}


@router.post("")
def route_create(
    body: CreateBody,
    svc: CasefileService = Depends(casefile_service),
) -> PersonOnlyResponse | ErrorResponse:
    if svc.actor_id is None:
        return {"error": "authentication required"}
    person = svc.create_person(
        display_name=body.get("display_name"),
        first_name=body.get("first_name"),
        last_name=body.get("last_name"),
        expected_location=body.get("expected_location"),
        current_location=body.get("current_location"),
        last_seen=body.get("last_seen"),
        cedula=body.get("cedula"),
        notas=body.get("notas", ""),
        minor=body.get("is_minor", False),
        status=body.get("status"),
    )
    return {"person": _person_dict(person)}


@router.get("/{person_id}")
def route_get(
    person_id: int,
    svc: CasefileService = Depends(casefile_service),
) -> PersonResponse | ErrorResponse:
    result = svc.get(person_id)
    if result is None:
        return {"error": "not found"}
    person = result["person"]
    return {
        "person": _person_dict(person),
        "faces": [
            {
                "id": f.id,
                "image_id": f.image_id,
                "person_id": f.person_id,
                "confirmation": f.confirmation,
                "det_score": f.det_score,
            }
            for f in result["faces"]
        ],
        "reports": [
            {
                "id": r.id,
                "kind": r.kind,
                "location": r.location,
                "notes": r.notes,
                "reporter": r.reporter,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in result["reports"]
        ],
        "comments": [
            {
                "id": c.id,
                "author": c.author,
                "body": c.body,
                "created_at": str(c.created_at) if c.created_at else None,
            }
            for c in result["comments"]
        ],
    }


@router.patch("/{person_id}")
def route_update_identity(
    person_id: int,
    body: UpdateBody,
    svc: CasefileService = Depends(casefile_service),
) -> PersonOnlyResponse | ErrorResponse:
    # Only the keys actually present in the body are updated (is_minor maps to
    # the column of the same name).
    fields = {k: body[k] for k in UpdateBody.__annotations__ if k in body}  # type: ignore[literal-required]
    if not fields:
        return {"error": "no fields to update"}
    if "status" in fields:
        try:
            fields["status"] = PersonStatus(fields["status"])
        except ValueError:
            return {"error": "invalid status"}
    result = svc.update_identity(person_id, **fields)
    if result is None:
        return {"error": "not found"}
    return {"person": _person_dict(result)}


@router.post("/{person_id}/reports")
def route_add_report(
    person_id: int,
    body: ReportBody,
    svc: CasefileService = Depends(casefile_service),
) -> ReportIdResponse:
    if svc.actor_id is None:
        return {"report_id": None}
    kind = ReportKind(body.get("kind", ReportKind.NOTE))
    report = svc.add_report(
        person_id=person_id,
        kind=kind,
        location=body.get("location", ""),
        seen_at=None,
        notes=body.get("notes", ""),
        image_id=body.get("image_id"),
    )
    return {"report_id": report.id}


@router.post("/{person_id}/comments")
def route_add_comment(
    person_id: int,
    body: CommentBody,
    svc: CasefileService = Depends(casefile_service),
) -> CommentIdResponse:
    if svc.actor_id is None:
        return {"comment_id": None}
    comment = svc.add_comment(person_id=person_id, body=body["body"])
    return {"comment_id": comment.id}


@router.post("/{person_id}/archive")
def route_archive(
    person_id: int,
    svc: CasefileService = Depends(casefile_service),
) -> ArchiveResponse | ErrorResponse:
    if svc.actor_id is None:
        return {"error": "authentication required"}
    result = svc.archive(person_id)
    if result is None:
        return {"error": "not found"}
    return {"archived": True, "person_id": person_id}


@router.post("/merge")
def route_merge(
    body: MergeBody,
    svc: CasefileService = Depends(casefile_service),
) -> MergeResponse | ErrorResponse:
    if svc.actor_id is None:
        return {"error": "authentication required"}
    result = svc.merge(survivor_id=body["survivor_id"], loser_id=body["loser_id"])
    if result is None:
        return {"error": "not found"}
    return {"merged": True, "survivor_id": body["survivor_id"]}


@router.post("/create-and-assign")
def route_create_and_assign(
    body: CreateAssignBody,
    svc: IdentifyService = Depends(identify_service),
) -> CreateAssignResponse | ErrorResponse:
    if svc.actor_id is None:
        return {"error": "authentication required"}
    level = ConfirmationLevel(body.get("level", ConfirmationLevel.PROBABLE))
    result = svc.create_person_and_assign(
        face_id=body["face_id"],
        display_name=body.get("display_name"),
        attributes=body.get("attributes"),
        level=level,
    )
    if result is None:
        return {"error": "face not found"}
    face = result["face"]
    face_id = face.id if face is not None else None
    return {"person_id": result["person"].id, "face_id": face_id}
