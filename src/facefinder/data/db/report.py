from datetime import UTC, datetime

from sqlmodel import Column, Field, SQLModel, col, select

from facefinder.constants.enums import ReportKind
from facefinder.constants.types import ReportData
from facefinder.data.db._base import Manager, enum_column, scope


class Report(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    person_id: int = Field(foreign_key="person.id")
    image_id: int | None = Field(default=None, foreign_key="image.id")
    kind: ReportKind = Field(
        default=ReportKind.NOTE, sa_column=Column(enum_column(ReportKind), nullable=False)
    )
    location: str = ""
    seen_at: datetime | None = None
    reporter: int | None = Field(default=None, foreign_key="user.id")
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class _Reports(Manager[Report, ReportData]):
    def for_person(self, person_id: int) -> list[ReportData]:
        with scope() as s:
            stmt = (
                select(Report)
                .where(Report.person_id == person_id)
                .order_by(col(Report.created_at).desc())
            )
            return self._many(list(s.exec(stmt).all()))


Reports = _Reports(Report, ReportData)
