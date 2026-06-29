from facefinder.constants import settings
from facefinder.constants.enums import UserRole
from facefinder.constants.types import UserData
from facefinder.data import Users
from facefinder.domains.auth import (
    create_token,
    decode_subject,
    hash_password,
    verify_password,
)
from facefinder.services.base import BaseService

__all__ = ["AuthService", "UserData"]

MIN_PASSWORD_LENGTH = 6


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")


class AuthService(BaseService):
    def user_count(self) -> int:
        return len(Users.all())

    def register(
        self,
        email: str,
        password: str,
        display_name: str,
        role: UserRole = UserRole.CURATOR,
    ) -> UserData:
        _validate_password(password)
        if Users.by_email(email):
            raise ValueError("email already registered")
        # Bootstrap: the very first account on a fresh install becomes admin, so
        # there's always someone who can create the rest. After that, creation is
        # gated to admins at the API layer.
        if self.user_count() == 0:
            role = UserRole.ADMIN
        return Users.create(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            role=role,
        )

    def change_password(self, user_id: int, current: str, new: str) -> bool:
        """Self-service: verify the current password before setting the new one."""
        _validate_password(new)
        user = Users.get(user_id)
        if user is None or not verify_password(current, user.password_hash):
            return False
        Users.update(user_id, password_hash=hash_password(new))
        return True

    def reset_password(self, user_id: int, new: str) -> UserData | None:
        """Admin: set a password without knowing the old one."""
        _validate_password(new)
        return Users.update(user_id, password_hash=hash_password(new))

    def set_active(self, user_id: int, active: bool) -> UserData | None:
        return Users.update(user_id, is_active=active)

    def set_role(self, user_id: int, role: UserRole) -> UserData | None:
        return Users.update(user_id, role=role)

    def update_profile(
        self, user_id: int, display_name: str | None = None, email: str | None = None
    ) -> UserData | None:
        fields: dict[str, object] = {}
        if display_name is not None:
            fields["display_name"] = display_name
        if email is not None:
            existing = Users.by_email(email)
            if existing is not None and existing.id != user_id:
                raise ValueError("email already registered")
            fields["email"] = email
        if not fields:
            return Users.get(user_id)
        return Users.update(user_id, **fields)

    def login(self, email: str, password: str) -> tuple[str, UserData] | None:
        user = Users.by_email(email)
        if user is None or not user.is_active or user.id is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return create_token(user.id), user

    def current_user(self, token: str) -> UserData | None:
        sub = decode_subject(token)
        if sub is None:
            return None
        return Users.get(sub)

    def list_users(self) -> list[UserData]:
        return Users.all()


def seed_default_admin() -> UserData | None:
    """Create the seeded admin on a fresh install (empty user table), so the app
    is usable without first-run setup. Credentials come from settings.seed, i.e.
    SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD / SEED_ADMIN_NAME in .env (gitignored).
    No password configured → no seeding (there is no built-in default password).
    """
    if not settings.seed.password:
        return None
    svc = AuthService()
    if svc.user_count() > 0:
        return None
    return svc.register(
        email=settings.seed.email,
        password=settings.seed.password,
        display_name=settings.seed.name,
    )
