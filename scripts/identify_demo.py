"""Prove faces cluster: for each stored face, show its nearest *other* faces
with real cosine distances. (Person-grouped `identify()` isn't useful yet — no
persons are assigned, so every unassigned face shares the same None group.)
"""

from facefinder.constants import settings
from facefinder.data import Faces, init_db


def band(sim: float) -> str:
    if sim >= settings.scores.match_strong:
        return "strong"
    if sim >= settings.scores.match_possible:
        return "possible"
    return "weak"


def main() -> None:
    init_db()
    faces = Faces.all()

    for face in faces:
        print(f"\n=== Face id={face.id} (image_id={face.image_id}) — nearest others ===")
        hits = Faces.nearest(face.embedding, k=5, exclude_id=face.id)
        for h in hits:
            sim = 1.0 - h.distance
            print(
                f"  face {h.id:>2} (image {h.image_id}) | sim={sim:.3f} "
                f"dist={h.distance:.3f} | {band(sim)}"
            )


if __name__ == "__main__":
    main()
