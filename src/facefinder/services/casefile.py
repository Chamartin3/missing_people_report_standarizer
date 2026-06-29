from datetime import UTC, datetime

from typing_extensions import TypedDict

from facefinder.constants.enums import PersonStatus, ReportKind
from facefinder.constants.types import CommentData, FaceData, PersonData, ReportData
from facefinder.data import Comments, Faces, Persons, Reports
from facefinder.services.base import BaseService

__all__ = ["CasefileResult", "CasefileService"]


class CasefileResult(TypedDict):
    person: PersonData
    faces: list[FaceData]
    reports: list[ReportData]
    comments: list[CommentData]


class CasefileService(BaseService):
    def create_person(
        self,
        display_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        expected_location: str | None = None,
        current_location: str | None = None,
        last_seen: str | None = None,
        cedula: str | None = None,
        notas: str = "",
        minor: bool = False,
        status: PersonStatus | str | None = None,
    ) -> PersonData:
        self.require_actor()
        # Fall back to "First Last" for the display name when none is given.
        name = display_name or " ".join(p for p in (first_name, last_name) if p) or None
        return Persons.create(
            display_name=name,
            first_name=first_name or None,
            last_name=last_name or None,
            expected_location=expected_location or None,
            current_location=current_location or None,
            last_seen=last_seen or None,
            cedula=cedula or None,
            is_minor=bool(minor),
            notas=notas or "",
            status=PersonStatus(status) if status else PersonStatus.MISSING,
        )

    def list_persons(self) -> list[PersonData]:
        return [
            p
            for p in Persons.all()
            if p.deleted_at is None and p.merged_into is None
        ]

    def get(self, person_id: int) -> CasefileResult | None:
        person = Persons.get(person_id)
        if person is None:
            return None

        survivor_id = _survivor(person)
        if survivor_id != person_id:
            return self.get(survivor_id)

        faces = Faces.for_person(person_id)
        reports = Reports.for_person(person_id)
        comments = Comments.for_person(person_id)

        # status is a human-set case state (missing/found/…), kept as stored.
        return {"person": person, "faces": faces, "reports": reports, "comments": comments}

    def update_identity(self, person_id: int, **fields: object) -> PersonData | None:
        return Persons.update(person_id, **fields)

    def add_report(
        self,
        person_id: int,
        kind: ReportKind,
        location: str = "",
        seen_at: datetime | None = None,
        notes: str = "",
        image_id: int | None = None,
    ) -> ReportData:
        return Reports.create(
            person_id=person_id,
            kind=kind,
            reporter=self.require_actor(),
            location=location,
            seen_at=seen_at,
            notes=notes,
            image_id=image_id,
        )

    def add_comment(self, person_id: int, body: str) -> CommentData:
        return Comments.create(person_id=person_id, author=self.require_actor(), body=body)

    def archive(self, person_id: int) -> PersonData | None:
        return Persons.update(person_id, deleted_at=datetime.now(UTC))

    def merge(self, survivor_id: int, loser_id: int) -> PersonData | None:
        user_id = self.require_actor()
        if Persons.get(survivor_id) is None or Persons.get(loser_id) is None:
            return None

        faces = Faces.for_person(loser_id)
        reports = Reports.for_person(loser_id)
        comments = Comments.for_person(loser_id)
        moved = {
            "face_ids": [f.id for f in faces],
            "report_ids": [r.id for r in reports],
            "comment_ids": [c.id for c in comments],
        }

        # ponytail: multi-statement, not one transaction (each manager owns its
        # session). Re-running is idempotent; wrap in a managed tx only if a
        # partial merge ever shows up in practice.
        for f in faces:
            if f.id is not None:
                Faces.assign(f.id, survivor_id, f.confirmation, f.confidence, user_id)
        for r in reports:
            if r.id is not None:
                Reports.update(r.id, person_id=survivor_id)
        for c in comments:
            if c.id is not None:
                Comments.update(c.id, person_id=survivor_id)

        Persons.update(loser_id, merged_into=survivor_id)
        # No PersonMerge table — the merge is just logged on the survivor's record.
        Reports.create(
            person_id=survivor_id,
            kind=ReportKind.MERGE,
            reporter=user_id,
            notes=f"merged from person {loser_id}: {moved}",
        )
        return Persons.get(survivor_id)


def _survivor(person: PersonData) -> int:
    if person.merged_into is not None:
        nxt = Persons.get(person.merged_into)
        if nxt is None:
            raise ValueError("merged_into points to missing person")
        return _survivor(nxt)
    if person.id is None:
        raise ValueError("person has no id")
    return person.id
