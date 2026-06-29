from datetime import UTC, datetime, timedelta

from facefinder.constants import settings
from facefinder.domains.auth.security import decode_jwt, encode_jwt


def create_token(user_id: int) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=settings.auth.jwt_expiry_minutes)
    return encode_jwt(
        {"sub": str(user_id), "iat": int(now.timestamp()), "exp": int(exp.timestamp())},
        settings.auth.jwt_secret,
    )


def decode_subject(token: str) -> int | None:
    # ponytail: broad except keeps jwt isolated in security.py; any decode
    # failure (expired/invalid/missing sub) just means "no user".
    try:
        payload = decode_jwt(token, settings.auth.jwt_secret)
    except Exception:
        return None
    sub = payload.get("sub")
    # JWT `sub` is a string per RFC 7519; reject a non-numeric subject.
    if not isinstance(sub, str) or not sub.isdigit():
        return None
    return int(sub)
