"""Core password generation logic."""

from __future__ import annotations

import base64
import hashlib
from typing import List

from app import models
from app.seed_expander import SeedExpander
from app.validators import validate_constraints

UPPER_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER_CHARS = "abcdefghijklmnopqrstuvwxyz"
DIGIT_CHARS = "0123456789"
SPECIAL_CHARS = "!@#$%^&*()-_=+[]{};:,.<>/?\\|\"'`~"

DEFAULT_CONSTRAINTS = models.PasswordConstraints(
    length=24,
    upper=0,
    lower=0,
    digits=0,
    specials=0,
    mask=0,
)


def _legacy_password(
    username: str, resource: str, secret: str, generation_version: int
) -> str:
    raw = f"{username}:{resource}:{generation_version}:{secret}"
    data = raw.encode("utf-8")
    b64_data = base64.urlsafe_b64encode(data)
    digest = hashlib.sha256(b64_data).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8")


def _derive_seed(
    username: str, resource: str, secret: str, generation_version: int
) -> bytes:
    raw = f"{username}:{resource}:{generation_version}:{secret}"
    data = raw.encode("utf-8")
    return hashlib.sha256(data).digest()


def _pick_chars(expander: SeedExpander, charset: str, count: int) -> List[str]:
    if count <= 0:
        return []
    return [charset[expander.randbelow(len(charset))] for _ in range(count)]


def _escape_specials(
    characters: List[str],
    mask: int,
) -> tuple[List[str], int]:
    escaped: List[str] = []
    masked = 0
    for char in characters:
        if char in SPECIAL_CHARS and masked < mask:
            escaped.append("\\")
            escaped.append(char)
            masked += 1
        else:
            escaped.append(char)
    return escaped, masked


def _deterministic_shuffle(
    expander: SeedExpander,
    characters: List[str],
) -> List[str]:
    shuffled = characters[:]
    for i in range(len(shuffled) - 1, 0, -1):
        j = expander.randbelow(i + 1)
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
    return shuffled


def _generate_with_constraints(
    username: str,
    resource: str,
    secret: str,
    constraints: models.PasswordConstraints,
    generation_version: int,
) -> str:
    seed = _derive_seed(username, resource, secret, generation_version)
    expander = SeedExpander(seed)

    characters: List[str] = []
    characters.extend(_pick_chars(expander, UPPER_CHARS, constraints.upper))
    characters.extend(_pick_chars(expander, LOWER_CHARS, constraints.lower))
    characters.extend(_pick_chars(expander, DIGIT_CHARS, constraints.digits))
    characters.extend(
        _pick_chars(expander, SPECIAL_CHARS, constraints.specials)
    )

    fill = (
        constraints.length
        - constraints.upper
        - constraints.lower
        - constraints.digits
        - constraints.specials
        - constraints.mask
    )
    characters.extend(_pick_chars(expander, LOWER_CHARS, fill))

    characters = _deterministic_shuffle(expander, characters)
    characters, _ = _escape_specials(characters, constraints.mask)
    return "".join(characters)


def generate_password_from_request(
    request: models.PasswordGenerationRequest,
) -> str:
    constraints = validate_constraints(request.profile.constraints)
    username = request.profile.username
    resource = request.profile.resource
    secret = request.secret
    generation_version = request.profile.generation_version

    if constraints == DEFAULT_CONSTRAINTS:
        return _legacy_password(username, resource, secret, generation_version)

    return _generate_with_constraints(
        username, resource, secret, constraints, generation_version
    )


def generate_password(
    username: str,
    resource: str,
    secret: str,
    length: int = 16,
    upper: int = 2,
    lower: int = 2,
    digits: int = 2,
    specials: int = 2,
    mask: int = 1,
    generation_version: int = 1,
) -> str:
    request = models.PasswordGenerationRequest(
        profile=models.PasswordProfile(
            username=username,
            resource=resource,
            constraints=models.PasswordConstraints(
                length=length,
                upper=upper,
                lower=lower,
                digits=digits,
                specials=specials,
                mask=mask,
            ),
            generation_version=generation_version,
        ),
        secret=secret,
    )

    return generate_password_from_request(request)
