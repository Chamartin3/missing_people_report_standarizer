from datetime import UTC, datetime

from sqlalchemy import JSON, Column, func
from sqlmodel import Field, SQLModel, col, select

from facefinder.constants.types import ImageData
from facefinder.data.db._base import Manager, scope


class Image(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # Not unique: a curator can force-store a byte-identical image as "new"
    # (see UploadService.store(force=...)); by_hash still powers dedup warnings.
    sha256: str = Field(index=True)
    path: str
    format: str
    source: str = ""
    uploaded_by: int | None = Field(default=None, foreign_key="user.id")
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    processed_at: datetime | None = None
    meta: dict[str, object] = Field(default_factory=dict, sa_column=Column(JSON))


class _Images(Manager[Image, ImageData]):
    def by_hash(self, h: str) -> ImageData | None:
        with scope() as s:
            return self._one(s.exec(select(Image).where(Image.sha256 == h)).first())

    def stats(self) -> dict[str, int]:
        """Total images and how many have been processed (faces detected)."""
        with scope() as s:
            total = int(s.exec(select(func.count()).select_from(Image)).one())
            processed = int(
                s.exec(
                    select(func.count())
                    .select_from(Image)
                    .where(col(Image.processed_at).is_not(None))
                ).one()
            )
        return {"total": total, "processed": processed, "unprocessed": total - processed}

    def page(
        self, limit: int = 24, offset: int = 0, processed: bool | None = None
    ) -> tuple[list[ImageData], int]:
        """Newest-first page of images plus the total count, for the list view.
        processed=True/False filters by detection state; None returns all."""
        with scope() as s:
            count_q = select(func.count()).select_from(Image)
            rows_q = select(Image).order_by(col(Image.id).desc())
            if processed is not None:
                cond = (
                    col(Image.processed_at).is_not(None)
                    if processed
                    else col(Image.processed_at).is_(None)
                )
                count_q = count_q.where(cond)
                rows_q = rows_q.where(cond)
            total = int(s.exec(count_q).one())
            rows = list(s.exec(rows_q.limit(limit).offset(offset)).all())
            return self._many(rows), total

    def recent(self, limit: int = 8) -> list[ImageData]:
        with scope() as s:
            return self._many(
                list(s.exec(select(Image).order_by(col(Image.id).desc()).limit(limit)).all())
            )


Images = _Images(Image, ImageData)
