from facefinder.data import Faces, Persons, Users, init_db
from facefinder.services.identify import IdentifyService


def main() -> None:
    init_db()
    identify = IdentifyService(Users.get(1))

    unassigned = [f for f in Faces.all() if f.person_id is None]
    print(f"Unassigned faces: {len(unassigned)}")

    people = Persons.all()
    print(f"Existing people: {len(people)}")
    for p in people:
        print(f"  Person id={p.id} name={p.display_name!r} status={p.status}")

    if not unassigned:
        print("No unassigned faces to curate.")
        return

    face = unassigned[0]
    print(f"\nAssigning face id={face.id} to a new Person...")
    result = identify.create_person_and_assign(
        face_id=face.id,  # type: ignore[arg-type]
        display_name="Test Person",
        attributes={"note": "demo"},
        level="probable",
    )

    if result:
        p = result["person"]
        f = result["face"]
        print(f"Created Person id={p.id} name={p.display_name!r}")
        print(
            f"Face id={f.id} now: person_id={f.person_id} "
            f"confirmation={f.confirmation} assigned_by={f.assigned_by}"
        )

    remaining = len([f for f in Faces.all() if f.person_id is None])
    print(f"\nRemaining unassigned: {remaining}")


if __name__ == "__main__":
    main()
