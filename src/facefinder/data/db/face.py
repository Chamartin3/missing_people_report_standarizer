from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import func
from sqlmodel import ARRAY, Column, Field, Integer, SQLModel, col, select

from facefinder.constants.enums import ConfirmationLevel
from facefinder.constants.types import DetectedFace, FaceData
from facefinder.data.db._base import Manager, enum_column, scope


@dataclass
class FaceHit:
    """A nearest-neighbour row: what dedup needs (id/person_id/distance) plus
    image_id for callers that want to point back at the source image, and
    crop_path so callers can collapse byte-identical crops (same image stored
    twice → same content-addressed crop key)."""

    id: int
    image_id: int
    person_id: int | None
    distance: float
    crop_path: str | None = None


class Face(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    image_id: int = Field(foreign_key="image.id")
    crop_path: str | None = None
    bbox: list[int] = Field(sa_column=Column(ARRAY(Integer)))
    embedding: list[float] = Field(sa_column=Column(Vector(512)))
    det_score: float
    person_id: int | None = Field(default=None, foreign_key="person.id")
    confidence: float | None = None
    confirmation: ConfirmationLevel = Field(
        default=ConfirmationLevel.SUGGESTED,
        sa_column=Column(enum_column(ConfirmationLevel), nullable=False),
    )
    assigned_by: int | None = Field(default=None, foreign_key="user.id")
    assigned_at: datetime | None = None


class _Faces(Manager[Face, FaceData]):
    def for_person(self, person_id: int) -> list[FaceData]:
        with scope() as s:
            return self._many(
                list(s.exec(select(Face).where(Face.person_id == person_id)).all())
            )

    def unassigned(self) -> list[FaceData]:
        with scope() as s:
            return self._many(
                list(s.exec(select(Face).where(col(Face.person_id).is_(None))).all())
            )

    def for_image(self, image_id: int) -> list[FaceData]:
        with scope() as s:
            return self._many(
                list(s.exec(select(Face).where(Face.image_id == image_id)).all())
            )

    def page(
        self,
        *,
        assigned: bool | None = None,
        person_id: int | None = None,
        confirmation: str | None = None,
        limit: int = 24,
        offset: int = 0,
    ) -> tuple[list[FaceData], int]:
        """Filtered, paginated face listing + total matching count."""
        conds = []
        if person_id is not None:
            conds.append(Face.person_id == person_id)
        elif assigned is True:
            conds.append(col(Face.person_id).is_not(None))
        elif assigned is False:
            conds.append(col(Face.person_id).is_(None))
        if confirmation is not None:
            conds.append(Face.confirmation == confirmation)
        with scope() as s:
            total = s.exec(select(func.count()).select_from(Face).where(*conds)).one()
            rows = s.exec(
                select(Face).where(*conds).order_by(col(Face.id).desc()).limit(limit).offset(offset)
            ).all()
            return self._many(list(rows)), int(total)

    def count_unidentified(self) -> int:
        with scope() as s:
            return int(
                s.exec(
                    select(func.count()).select_from(Face).where(col(Face.person_id).is_(None))
                ).one()
            )

    def bulk_create(
        self,
        image_id: int,
        faces: list[DetectedFace],
        crop_paths: Sequence[str | None] | None = None,
    ) -> list[FaceData]:
        paths = crop_paths if crop_paths is not None else [None] * len(faces)
        with scope() as s:
            objs = [
                Face(
                    image_id=image_id,
                    crop_path=p,
                    bbox=f["bbox"],
                    embedding=f["embedding"],
                    det_score=f["det_score"],
                )
                for f, p in zip(faces, paths, strict=True)
            ]
            for obj in objs:
                s.add(obj)
            s.commit()
            for obj in objs:
                s.refresh(obj)
            return self._many(objs)

    def assign(
        self,
        face_id: int,
        person_id: int | None,
        confirmation: ConfirmationLevel,
        confidence: float | None,
        user_id: int | None,
    ) -> FaceData | None:
        with scope() as s:
            face = s.get(Face, face_id)
            if face is None:
                return None
            face.person_id = person_id
            face.confirmation = confirmation
            face.confidence = confidence
            face.assigned_by = user_id
            face.assigned_at = datetime.now(UTC)
            s.add(face)
            s.commit()
            s.refresh(face)
            return self._data.model_validate(face)

    def nearest(self, v: list[float], k: int = 20, exclude_id: int | None = None) -> list[FaceHit]:
        with scope() as s:
            # pgvector adds cosine_distance to the column at runtime; the field is
            # typed list[float], so the attribute access is invisible to pyright.
            dist = Face.embedding.cosine_distance(v).label("dist")  # pyright: ignore[reportAttributeAccessIssue]
            stmt = select(Face, dist).order_by(dist).limit(k)
            if exclude_id is not None:
                stmt = stmt.where(Face.id != exclude_id)
            hits: list[FaceHit] = []
            for face, d in s.exec(stmt).all():
                if face.id is None:
                    continue
                hits.append(
                    FaceHit(
                        id=face.id,
                        image_id=face.image_id,
                        person_id=face.person_id,
                        distance=float(d),
                        crop_path=face.crop_path,
                    )
                )
            return hits


Faces = _Faces(Face, FaceData)
