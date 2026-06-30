from pathlib import Path

from facefinder.data import init_db
from facefinder.services.upload import UploadService

SAMPLE_DIR = Path("sample_images")


def main() -> None:
    init_db()
    uploads = UploadService()

    files = sorted(
        p
        for p in SAMPLE_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic", ".webp"}
    )

    for fpath in files:
        data = fpath.read_bytes()
        stored = uploads.store(data, filename=fpath.name, source="demo_upload")
        status = stored["status"]
        if status != "created" or stored["image"] is None:
            print(f"{status.upper():10s} {fpath.name}")
            continue
        result = uploads.process(stored["image"].id)
        assert result is not None
        print(f"{status.upper():10s} {fpath.name}: {len(result['faces'])} face(s)")
        for i, f in enumerate(result["faces"]):
            cands = result["candidates"][i]
            print(f"  face {f.id}: {len(cands)} candidate groups")
            for c in cands[:3]:
                print(f"    {c.band:8s} sim={c.similarity:.3f} person_id={c.person_id}")

    print("\n--- re-running to test dedup ---")
    for fpath in files:
        data = fpath.read_bytes()
        stored = uploads.store(data, filename=fpath.name)
        print(f"{stored['status'].upper():10s} {fpath.name}")


if __name__ == "__main__":
    main()
