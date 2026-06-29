from collections.abc import Generator, Sequence
from contextlib import contextmanager
from enum import StrEnum
from typing import Generic, TypeVar

import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select

from facefinder.constants import settings

_engine = create_engine(settings.database.url, echo=False)


def init_db() -> None:
    with _engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    SQLModel.metadata.create_all(_engine)
    with _engine.connect() as conn:
        conn.execute(text("ALTER TABLE face ADD COLUMN IF NOT EXISTS crop_path text"))
        conn.execute(text("ALTER TABLE image ADD COLUMN IF NOT EXISTS processed_at timestamp"))
        # 'admin' role was added after 'curator'; ensure the PG enum has it.
        conn.execute(text("COMMIT"))  # ALTER TYPE ... ADD VALUE can't run in a tx block
        conn.execute(text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'admin'"))
        # sha256 was UNIQUE; drop it so a forced re-upload (image marked "new")
        # can store a byte-identical copy. Keep a plain index for dedup lookups.
        conn.execute(text("DROP INDEX IF EXISTS ix_image_sha256"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_image_sha256 ON image (sha256)"))
        # Pre-existing images already had faces detected under the old one-shot
        # upload — backfill so they don't read as "not processed".
        conn.execute(
            text(
                "UPDATE image SET processed_at = uploaded_at "
                "WHERE processed_at IS NULL "
                "AND id IN (SELECT DISTINCT image_id FROM face)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_face_embedding_hnsw "
                "ON face USING hnsw (embedding vector_cosine_ops)"
            )
        )
        conn.commit()


@contextmanager
def scope() -> Generator[Session, None, None]:
    session = Session(_engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()


@contextmanager
def atomic() -> Generator[Session, None, None]:
    with scope() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


TableT = TypeVar("TableT", bound=SQLModel)
DataT = TypeVar("DataT", bound=BaseModel)


def enum_column(enum_cls: type[StrEnum]) -> sa.Enum:
    """Single source of truth for enum <-> DB mapping.

    SQLModel's default maps a Python enum column by member *name* (UPPERCASE),
    but our enums are StrEnum whose *values* are lowercase. That mismatch is
    what let 'suggested' and 'SUGGESTED' both land in one column. Keying the PG
    enum on the value (via values_callable) makes the StrEnum value the only
    truth: DB labels == enum values, everywhere.
    """

    def values(members: type[StrEnum]) -> list[str]:
        return [m.value for m in members]

    return sa.Enum(enum_cls, values_callable=values, name=enum_cls.__name__.lower())


class Manager(Generic[TableT, DataT]):
    """CRUD over one table that always returns its pydantic data model, never
    the SQLModel row — so nothing above the data layer ever touches the ORM.
    Subclass to add entity-specific queries (see Faces, Reports, ...).
    """

    def __init__(self, table: type[TableT], data: type[DataT]) -> None:
        self._table = table
        self._data = data

    def _one(self, row: TableT | None) -> DataT | None:
        return self._data.model_validate(row) if row is not None else None

    def _many(self, rows: Sequence[TableT]) -> list[DataT]:
        return [self._data.model_validate(row) for row in rows]

    def get(self, id: int) -> DataT | None:
        with scope() as s:
            return self._one(s.get(self._table, id))

    def all(self) -> list[DataT]:
        with scope() as s:
            return self._many(list(s.exec(select(self._table)).all()))

    def create(self, **kw: object) -> DataT:
        with scope() as s:
            obj = self._table(**kw)
            s.add(obj)
            s.commit()
            s.refresh(obj)
            return self._data.model_validate(obj)

    def update(self, id: int, **kw: object) -> DataT | None:
        with scope() as s:
            obj = s.get(self._table, id)
            if obj is None:
                return None
            for attr, value in kw.items():
                setattr(obj, attr, value)
            s.add(obj)
            s.commit()
            s.refresh(obj)
            return self._data.model_validate(obj)
