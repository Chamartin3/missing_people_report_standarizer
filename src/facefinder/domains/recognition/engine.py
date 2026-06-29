import insightface
import numpy as np

from facefinder.constants import settings
from facefinder.constants.types import DetectedFace

_app: insightface.app.FaceAnalysis | None = None


def _get_app() -> insightface.app.FaceAnalysis:
    global _app
    if _app is None:
        _app = insightface.app.FaceAnalysis(name="buffalo_l")
        _app.prepare(ctx_id=-1)
    return _app


def detect_and_embed(rgb: np.ndarray) -> list[DetectedFace]:
    app = _get_app()
    faces = app.get(rgb)
    results: list[DetectedFace] = []
    for face in faces:
        if face.det_score < settings.scores.det_threshold:
            continue
        results.append(
            {
                "bbox": [int(v) for v in face.bbox],
                "det_score": float(face.det_score),
                "embedding": face.normed_embedding.tolist(),
            }
        )
    return results
