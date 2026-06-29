from typing import NotRequired

from fastapi import APIRouter, Depends
from typing_extensions import TypedDict

from facefinder.api.deps import auth_service, require_user
from facefinder.constants.types import UserData
from facefinder.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class UserPublic(TypedDict):
    id: int | None
    email: str
    display_name: str
    role: str
    is_active: bool


def public_user(u: UserData) -> UserPublic:
    """Never leak password_hash past the API boundary."""
    return {
        "id": u.id,
        "email": u.email,
        "display_name": u.display_name,
        "role": u.role,
        "is_active": u.is_active,
    }


class LoginBody(TypedDict):
    email: str
    password: str


class LoginResponse(TypedDict):
    token: str


class ErrorResponse(TypedDict):
    error: str


class PasswordBody(TypedDict):
    current_password: str
    new_password: str


class OkResponse(TypedDict):
    ok: bool


class ProfileBody(TypedDict):
    display_name: NotRequired[str]
    email: NotRequired[str]


# Account creation is intentionally NOT exposed here — there is no public signup.
# The first admin is created by the startup seed (settings.seed, from .env), and
# all further accounts are created by an admin via POST /users.


@router.post("/login")
def route_login(
    body: LoginBody,
    svc: AuthService = Depends(auth_service),
) -> LoginResponse | ErrorResponse:
    result = svc.login(body["email"], body["password"])
    if result is None:
        return {"error": "invalid credentials"}
    token, _user = result
    return {"token": token}


@router.get("/me")
def route_me(actor: UserData = Depends(require_user)) -> UserPublic:
    return public_user(actor)


@router.patch("/me")
def route_update_me(
    body: ProfileBody,
    svc: AuthService = Depends(auth_service),
    actor: UserData = Depends(require_user),
) -> UserPublic | ErrorResponse:
    if actor.id is None:
        return {"error": "not found"}
    try:
        updated = svc.update_profile(
            actor.id, display_name=body.get("display_name"), email=body.get("email")
        )
    except ValueError as e:
        return {"error": str(e)}
    return public_user(updated) if updated else {"error": "not found"}


@router.post("/password")
def route_change_password(
    body: PasswordBody,
    svc: AuthService = Depends(auth_service),
    actor: UserData = Depends(require_user),
) -> OkResponse | ErrorResponse:
    if actor.id is None:
        return {"error": "not found"}
    try:
        ok = svc.change_password(actor.id, body["current_password"], body["new_password"])
    except ValueError as e:
        return {"error": str(e)}
    if not ok:
        return {"error": "current password is incorrect"}
    return {"ok": True}
