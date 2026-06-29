from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from facefinder.constants import settings
from facefinder.constants.enums import MatchBand


class FaceHitRecord(Protocol):
    id: int
    person_id: int | None
    distance: float


@dataclass
class CandidateMatch:
    person_id: int | None
    display_name: str | None
    similarity: float
    distance: float
    band: MatchBand
    faces: list[int] = field(default_factory=list)


def _band(similarity: float) -> MatchBand:
    if similarity >= settings.scores.match_strong:
        return MatchBand.STRONG
    if similarity >= settings.scores.match_possible:
        return MatchBand.POSSIBLE
    return MatchBand.WEAK


def deduplicate(hits: Sequence[FaceHitRecord]) -> list[CandidateMatch]:
    by_person: dict[int | None, list[FaceHitRecord]] = {}
    for hit in hits:
        by_person.setdefault(hit.person_id, []).append(hit)

    candidates: list[CandidateMatch] = []
    for pid, group in by_person.items():
        best = min(group, key=lambda h: h.distance)
        distance = best.distance
        similarity = 1.0 - distance
        face_ids = [h.id for h in group]

        candidates.append(
            CandidateMatch(
                person_id=pid,
                display_name=None,
                similarity=round(similarity, 4),
                distance=round(distance, 4),
                band=_band(similarity),
                faces=sorted(face_ids),
            )
        )

    candidates.sort(key=lambda c: c.similarity, reverse=True)
    return candidates
