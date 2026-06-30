from pathlib import Path

import numpy as np
from PIL import Image as PILImage

from facefinder.data import Faces, Images, init_db
from facefinder.data.storage import crop as storage_crop
from facefinder.data.storage import load as storage_load
from facefinder.data.storage import save as storage_save
from facefinder.data.storage import sha256_bytes
from facefinder.domains.recognition.engine import detect_and_embed

SAMPLE_DIR = Path("sample_images")


def main() -> None:
    init_db()

    files = sorted(
        p
        for p in SAMPLE_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic", ".webp"}
    )

    for fpath in files:
        data = fpath.read_bytes()
        h = sha256_bytes(data)

        if Images.by_hash(h):
            print(f"SKIP (dup): {fpath.name}")
            continue

        path = storage_save(data, ext=fpath.suffix.lstrip(".").lower())
        fmt = fpath.suffix.lstrip(".").lower()
        image = Images.create(path=path, sha256=h, format=fmt, source="sample")

        np_img = np.array(PILImage.open(fpath).convert("RGB"))
        detected = detect_and_embed(np_img)

        if not detected:
            print(f"NO FACES: {fpath.name}")
            continue

        faces = Faces.bulk_create(image.id, detected)
        print(f"OK {fpath.name}: {len(faces)} face(s), image_id={image.id}")

        for face in faces:
            emb = face.embedding
            norm = float(np.linalg.norm(emb))
            assert len(emb) == 512, f"embedding length {len(emb)} != 512"
            assert abs(norm - 1.0) < 0.01, f"embedding not L2-normalised: norm={norm:.4f}"

        pil_img = storage_load(path)
        cropped = storage_crop(pil_img, detected[0]["bbox"])  # type: ignore[arg-type]
        assert cropped.size[0] > 0 and cropped.size[1] > 0, "crop is empty"


if __name__ == "__main__":
    main()
