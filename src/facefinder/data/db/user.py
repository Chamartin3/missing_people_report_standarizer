from datetime import UTC, datetime

from sqlmodel import Column, Field, SQLModel, select

from facefinder.constants.enums import UserRole
from facefinder.constants.types import UserData
from facefinder.data.db._base import Manager, enum_column, scope


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    display_name: str
    role: UserRole = Field(
        default=UserRole.CURATOR, sa_column=Column(enum_column(UserRole), nullable=False)
    )
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class _Users(Manager[User, UserData]):
    def by_email(self, email: str) -> UserData | None:
        with scope() as s:
            return self._one(s.exec(select(User).where(User.email == email)).first())


Users = _Users(User, UserData)
