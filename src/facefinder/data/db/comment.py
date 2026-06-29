from datetime import UTC, datetime

from sqlmodel import Field, SQLModel, col, select

from facefinder.constants.types import CommentData
from facefinder.data.db._base import Manager, scope


class Comment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    person_id: int = Field(foreign_key="person.id")
    author: int = Field(foreign_key="user.id")
    body: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class _Comments(Manager[Comment, CommentData]):
    def for_person(self, person_id: int) -> list[CommentData]:
        with scope() as s:
            stmt = (
                select(Comment)
                .where(Comment.person_id == person_id)
                .order_by(col(Comment.created_at).desc())
            )
            return self._many(list(s.exec(stmt).all()))


Comments = _Comments(Comment, CommentData)
