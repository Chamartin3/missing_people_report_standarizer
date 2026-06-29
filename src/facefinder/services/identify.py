import numpy as np
from typing_extensions import TypedDict

from facefinder.constants.enums import ConfirmationLevel
from facefinder.constants.types import (
    CandidateEntry,
    DetectedFace,
    FaceData,
    IdentifyCandidate,
    IdentifyImageResult,
    PersonData,
)
from facefinder.data import Faces, Persons
from facefinder.domains.curation.rules import check_transition
from facefinder.domains.recognition.dedup import CandidateMatch, deduplicate
from facefinder.domains.recognition.engine import detect_and_embed
from facefinder.services.base import BaseService

__all__ = ["IdentifyService", "PersonAssignResult"]


class PersonAssignResult(TypedDict):
    person: PersonData
    face: FaceData | None


class IdentifyService(BaseService):
    def identify(
        self, embedding: list[float], exclude_face_id: int | None = None
    ) -> list[CandidateMatch]:
        return deduplicate(Faces.nearest(embedding, exclude_id=exclude_face_id))

    def identify_from_image(self, rgb: np.ndarray) -> IdentifyImageResult:
        faces: list[DetectedFace] = detect_and_embed(rgb)
        results: list[IdentifyCandidate] = []
        for f in faces:
            entries: list[CandidateEntry] = [
                {"person_id": c.person_id, "similarity": c.similarity, "band": c.band}
                for c in self.identify(f["embedding"])
            ]
            results.append(
                {"bbox": f["bbox"], "det_score": f["det_score"], "candidates": entries}
            )
        return {"faces_detected": len(faces), "matches": results}

    def assign(
        self,
        face_id: int,
        person_id: int | None,
        level: ConfirmationLevel,
        confidence: float | None,
    ) -> FaceData | None:
        face = Faces.get(face_id)
        if face is None:
            return None
        check_transition(face.confirmation, level, self.actor_id)
        return Faces.assign(face_id, person_id, level, confidence, self.actor_id)

    def create_person_and_assign(
        self,
        face_id: int,
        display_name: str | None,
        attributes: dict[str, object] | None,
        level: ConfirmationLevel,
    ) -> PersonAssignResult | None:
        actor_id = self.require_actor()
        face = Faces.get(face_id)
        if face is None:
            return None

        person = Persons.create(display_name=display_name, attributes=attributes or {})
        if person.id is None:
            return None

        check_transition(face.confirmation, level, actor_id)
        updated = Faces.assign(face_id, person.id, level, None, actor_id)
        return {"person": person, "face": updated}
