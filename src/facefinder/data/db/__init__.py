"""Public surface of the db: the managers, nothing else.

Each manager owns one table and returns pydantic data models (constants.types),
so callers never see a SQLModel row. Table classes and the engine/session live
in the private modules behind these.
"""

from facefinder.data.db.comment import Comments
from facefinder.data.db.face import Faces
from facefinder.data.db.image import Images
from facefinder.data.db.person import Persons
from facefinder.data.db.report import Reports
from facefinder.data.db.user import Users

__all__ = ["Comments", "Faces", "Images", "Persons", "Reports", "Users"]
