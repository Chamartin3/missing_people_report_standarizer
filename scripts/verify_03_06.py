"""End-to-end verification of plans 03-06 against the live DB.

Run: docker compose start db && \
     DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/facefinder \
     STORAGE_DIR=storage python scripts/verify_03_06.py
"""

import io

from PIL import Image as PILImage

from facefinder.constants.enums import ConfirmationLevel, ReportKind
from facefinder.data import Faces, init_db
from facefinder.domains.curation.rules import TransitionError, check_transition
from facefinder.services.casefile import CasefileService
from facefinder.services.identify import IdentifyService
from facefinder.services.upload import UploadService

SAMPLE = "sample_images/WhatsApp Image 2026-06-29 at 3.31.06 PM.jpeg"


def reencode(path: str, quality: int) -> bytes:
    img = PILImage.open(path).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def main() -> None:
    init_db()
    ok = 0

    # ---- Plan 06: auth ----------------------------------------------------
    import time

    from facefinder.services.auth import AuthService

    auth = AuthService()
    email = f"curator+{int(time.time())}@example.org"
    user = auth.register(email, "s3cret-password", "Test Curator")
    assert user.id is not None
    tok_user = auth.login(email, "s3cret-password")
    assert tok_user is not None, "login failed"
    token, _ = tok_user
    assert auth.current_user(token) is not None, "current_user could not resolve a valid token"
    assert auth.login(email, "wrong") is None, "login accepted a wrong password"
    assert auth.current_user(token + "x") is None, "current_user accepted a tampered token"
    uid = user.id
    # services act on behalf of this curator
    uploads = UploadService(user)
    identify = IdentifyService(user)
    casefile = CasefileService(user)
    print(f"[06 auth] OK — register/login/current_user, bad creds rejected (uid={uid})")
    ok += 1

    # ---- Plan 03: upload --------------------------------------------------
    data = reencode(SAMPLE, quality=72)  # distinct bytes from the originally-extracted file
    res = uploads.store(data, filename="probe.jpg", source="verify")
    assert res["status"] == "created", f"expected created, got {res['status']}"
    assert res["image"] is not None
    proc = uploads.process(res["image"].id)
    assert proc is not None
    faces = proc["faces"]
    assert len(faces) >= 1, "process detected no faces"
    again = uploads.store(data, filename="probe.jpg", source="verify")
    assert again["status"] == "duplicate", "sha256 dedup failed on identical re-upload"
    probe_face = faces[0]
    print(f"[03 upload] OK — created {len(faces)} face(s); identical re-upload deduped")
    ok += 1

    # ---- Plan 04: curation ------------------------------------------------
    # machine may not jump past 'suggested'
    try:
        check_transition(ConfirmationLevel.SUGGESTED, ConfirmationLevel.CONFIRMED, user_id=None)
        raise AssertionError("machine was allowed to set CONFIRMED")
    except TransitionError:
        pass
    created = identify.create_person_and_assign(
        face_id=probe_face.id,
        display_name="Provisional Person",
        attributes={"note": "from verify"},
        level=ConfirmationLevel.PROBABLE,
    )
    assert created is not None
    person = created["person"]
    pid = person.id
    reloaded = Faces.get(probe_face.id)
    assert reloaded is not None and reloaded.person_id == pid
    assert reloaded.confirmation == ConfirmationLevel.PROBABLE
    assert reloaded.assigned_by == uid
    # climb the ladder to confirmed (probable -> confirmed by a human)
    bumped = identify.assign(probe_face.id, pid, ConfirmationLevel.CONFIRMED, 0.99)
    assert bumped is not None and bumped.confirmation == ConfirmationLevel.CONFIRMED
    print(f"[04 curation] OK — illegal transition blocked; face assigned + confirmed (pid={pid})")
    ok += 1

    # ---- Plan 05: casefile ------------------------------------------------
    casefile.add_report(pid, ReportKind.NOTE, location="Hospital X", notes="seen")
    casefile.add_comment(pid, body="family says scar on left forearm")
    cf = casefile.get(pid)
    assert cf is not None
    assert len(cf["reports"]) == 1 and len(cf["comments"]) == 1
    assert cf["person"].status == "identified", "person with a confirmed face should be identified"
    print(f"[05 casefile] OK — report+comment attached; status derived = {cf['person'].status}")

    # merge: make a second person from another face, merge it into the first
    other = next((f for f in faces if f.id != probe_face.id), None)
    if other is None:
        # use any existing unassigned face in the DB
        other = next((f for f in Faces.all() if f.person_id is None), None)
    if other is not None:
        c2 = identify.create_person_and_assign(
            other.id, "Dup Person", {}, ConfirmationLevel.PROBABLE
        )
        assert c2 is not None
        loser_id = c2["person"].id
        merged = casefile.merge(survivor_id=pid, loser_id=loser_id)
        assert merged is not None
        moved_face = Faces.get(other.id)
        assert moved_face is not None and moved_face.person_id == pid, "merge did not move face"
        # get(loser) must follow merged_into to the survivor
        followed = casefile.get(loser_id)
        assert followed is not None and followed["person"].id == pid, "merge redirect failed"
        print(
            f"[05 casefile] OK — merge moved faces to survivor; loser redirects (loser={loser_id})"
        )
    else:
        print("[05 casefile] SKIP merge — no spare face available")

    # archive (soft-delete)
    archived = casefile.archive(pid)
    assert archived is not None and archived.deleted_at is not None, (
        "archive did not set deleted_at"
    )
    print("[05 casefile] OK — archive soft-deleted (deleted_at set, row preserved)")
    ok += 1

    print(f"\nALL VERIFIED — {ok}/4 plan groups (03,04,05,06) passed end-to-end")


if __name__ == "__main__":
    main()
