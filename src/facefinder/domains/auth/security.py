"""Crypto + token boundary. All untyped third-party access (pwdlib, pyjwt)
is isolated here behind typed wrappers, so the rest of auth/ stays fully strict
against our own signatures instead of sprinkling `# type: ignore` everywhere.
"""

from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_hasher = PasswordHash([Argon2Hasher()])


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hash: str) -> bool:
    return _hasher.verify(password, hash)


# pyjwt's published stubs leave `key` partially unknown — a third-party stub gap.
# Contained to these two wrappers; everything above the seam is typed str/dict.
def encode_jwt(payload: dict[str, Any], secret: str) -> str:
    return jwt.encode(payload, secret, algorithm="HS256")  # pyright: ignore[reportUnknownMemberType]


def decode_jwt(token: str, secret: str) -> dict[str, Any]:
    return jwt.decode(token, secret, algorithms=["HS256"])  # pyright: ignore[reportUnknownMemberType]
