from datetime import UTC, datetime

from sqlmodel import JSON, Column, Field, SQLModel

from facefinder.constants.enums import PersonStatus
from facefinder.constants.types import PersonData
from facefinder.data.db._base import Manager, enum_column


class Person(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    expected_location: str | None = None
    current_location: str | None = None
    last_seen: str | None = None  # free text: when/where last seen
    cedula: str | None = Field(default=None, index=True)  # cédula de identidad
    is_minor: bool = False
    notas: str = ""
    status: PersonStatus = Field(
        default=PersonStatus.MISSING,
        sa_column=Column(enum_column(PersonStatus), nullable=False),
    )
    attributes: dict[str, object] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None
    merged_into: int | None = Field(default=None)


Persons = Manager(Person, PersonData)
