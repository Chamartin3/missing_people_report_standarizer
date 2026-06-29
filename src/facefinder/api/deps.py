from typing import Annotated

from fastapi import Depends, Header, HTTPException

from facefinder.constants.enums import UserRole
from facefinder.services.auth import AuthService, UserData
from facefinder.services.casefile import CasefileService
from facefinder.services.identify import IdentifyService
from facefinder.services.ocr import OcrService
from facefinder.services.upload import UploadService


def get_current_user(
    authorization: Annotated[str, Header()] = "",
) -> UserData | None:
    token = authorization.removeprefix("Bearer ").strip()
    return AuthService().current_user(token)


def require_user(
    user: UserData | None = Depends(get_current_user),
) -> UserData:
    """Any signed-in user. 401 otherwise."""
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return user


def require_admin(
    user: UserData = Depends(require_user),
) -> UserData:
    """Admin-only — gates account creation and user management."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="admin only")
    return user


def auth_service() -> AuthService:
    return AuthService()


def casefile_service(
    user: UserData | None = Depends(get_current_user),
) -> CasefileService:
    return CasefileService(user)


def identify_service(
    user: UserData | None = Depends(get_current_user),
) -> IdentifyService:
    return IdentifyService(user)


def upload_service(
    user: UserData | None = Depends(get_current_user),
) -> UploadService:
    return UploadService(user)


def ocr_service(
    user: UserData | None = Depends(get_current_user),
) -> OcrService:
    return OcrService(user)
