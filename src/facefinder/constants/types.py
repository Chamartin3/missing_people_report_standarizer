from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from typing_extensions import TypedDict

from facefinder.constants.enums import (
    ConfirmationLevel,
    MatchBand,
    PersonStatus,
    ReportKind,
    UserRole,
)

# --- recognition pipeline contracts (plain dicts, no DB) ---------------------


class DetectedFace(TypedDict):
    bbox: list[int]
    det_score: float
    embedding: list[float]


class CandidateEntry(TypedDict):
    person_id: int | None
    similarity: float
    band: MatchBand


class IdentifyCandidate(TypedDict):
    bbox: list[int]
    det_score: float
    candidates: Sequence[CandidateEntry]


class IdentifyImageResult(TypedDict):
    faces_detected: int
    matches: list[IdentifyCandidate]


# --- persisted-entity data models --------------------------------------------
# One pydantic model per table. Managers in facefinder.data.db return these
# (never the SQLModel rows), so nothing above the data layer touches the ORM.
# from_attributes lets a manager do Model.model_validate(orm_row).


class _Data(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserData(_Data):
    id: int | None
    email: str
    password_hash: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class ImageData(_Data):
    id: int | None
    sha256: str
    path: str
    format: str
    source: str
    uploaded_by: int | None
    uploaded_at: datetime
    processed_at: datetime | None
    meta: dict[str, object]


class FaceData(_Data):
    id: int | None
    image_id: int
    crop_path: str | None
    bbox: list[int]
    embedding: list[float]
    det_score: float
    person_id: int | None
    confidence: float | None
    confirmation: ConfirmationLevel
    assigned_by: int | None
    assigned_at: datetime | None


class PersonData(_Data):
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
    status: PersonStatus
    attributes: dict[str, object]
    created_at: datetime
    deleted_at: datetime | None
    merged_into: int | None


class ReportData(_Data):
    id: int | None
    person_id: int
    image_id: int | None
    kind: ReportKind
    location: str
    seen_at: datetime | None
    reporter: int | None
    notes: str
    created_at: datetime


class CommentData(_Data):
    id: int | None
    person_id: int
    author: int
    body: str
    created_at: datetime
