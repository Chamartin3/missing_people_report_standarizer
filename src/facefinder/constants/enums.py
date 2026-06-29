from enum import StrEnum


class ConfirmationLevel(StrEnum):
    SUGGESTED = "suggested"
    PROBABLE = "probable"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    REJECTED = "rejected"


class MatchBand(StrEnum):
    STRONG = "strong"
    POSSIBLE = "possible"
    WEAK = "weak"


class PersonStatus(StrEnum):
    MISSING = "missing"
    SEARCHING = "searching"
    FOUND = "found"
    REUNITED = "reunited"
    DECEASED = "deceased"


class ReportKind(StrEnum):
    NOTE = "note"
    MERGE = "merge"


class UserRole(StrEnum):
    CURATOR = "curator"
    ADMIN = "admin"


class StorageKind(StrEnum):
    IMAGES = "images"
    FACES = "faces"
