from typing import NotRequired

from fastapi import APIRouter, Depends
from typing_extensions import TypedDict

from facefinder.api.auth import UserPublic, public_user
from facefinder.api.deps import auth_service, require_admin
from facefinder.constants.enums import UserRole
from facefinder.constants.types import UserData
from facefinder.services.auth import AuthService

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


class UserListResponse(TypedDict):
    users: list[UserPublic]


class ErrorResponse(TypedDict):
    error: str


class CreateUserBody(TypedDict):
    email: str
    password: str
    display_name: NotRequired[str]
    role: NotRequired[str]


class UpdateUserBody(TypedDict):
    is_active: NotRequired[bool]
    role: NotRequired[str]
    new_password: NotRequired[str]


@router.get("")
def route_list(svc: AuthService = Depends(auth_service)) -> UserListResponse:
    return {"users": [public_user(u) for u in svc.list_users()]}


@router.post("")
def route_create(
    body: CreateUserBody,
    svc: AuthService = Depends(auth_service),
) -> UserPublic | ErrorResponse:
    try:
        user = svc.register(
            email=body["email"],
            password=body["password"],
            display_name=body.get("display_name", body["email"]),
            role=UserRole(body.get("role", UserRole.CURATOR)),
        )
    except ValueError as e:
        return {"error": str(e)}
    return public_user(user)


@router.patch("/{user_id}")
def route_update(
    user_id: int,
    body: UpdateUserBody,
    svc: AuthService = Depends(auth_service),
) -> UserPublic | ErrorResponse:
    updated: UserData | None = None
    if "is_active" in body:
        updated = svc.set_active(user_id, bool(body["is_active"]))
    if "role" in body:
        updated = svc.set_role(user_id, UserRole(body["role"]))
    if body.get("new_password"):
        try:
            updated = svc.reset_password(user_id, body["new_password"])
        except ValueError as e:
            return {"error": str(e)}
    if updated is None:
        return {"error": "user not found or no changes"}
    return public_user(updated)
