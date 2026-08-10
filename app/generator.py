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
    min_length=24,
    max_length=32,
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
    length_range = constraints.max_length - constraints.min_length + 1
    step = expander.randbelow(length_range)
    password_length = constraints.min_length + step
    typed_sum = (
        constraints.upper
        + constraints.lower
        + constraints.digits
        + constraints.specials
    )
    password_length = max(password_length, typed_sum)
    slack = max(0, password_length - typed_sum)
    planned_mask = min(constraints.mask, slack)
    target_length = password_length - planned_mask

    characters: List[str] = []

    def add_chars(pool: str, count: int) -> None:
        characters.extend(_pick_chars(expander, pool, count))

    add_chars(UPPER_CHARS, constraints.upper)
    add_chars(LOWER_CHARS, constraints.lower)
    add_chars(DIGIT_CHARS, constraints.digits)
    add_chars(SPECIAL_CHARS, constraints.specials)

    while len(characters) < target_length:
        pool_choice = expander.randbelow(4)
        if pool_choice == 0:
            add_chars(UPPER_CHARS, 1)
        elif pool_choice == 1:
            add_chars(LOWER_CHARS, 1)
        elif pool_choice == 2:
            add_chars(DIGIT_CHARS, 1)
        else:
            add_chars(SPECIAL_CHARS, 1)

    characters, _ = _escape_specials(characters, planned_mask)

    deficit = password_length - len(characters)
    while deficit > 0:
        add_chars(LOWER_CHARS, 1)
        deficit -= 1

    characters = _deterministic_shuffle(expander, characters)
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
    min_length: int = 12,
    max_length: int = 16,
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
                min_length=min_length,
                max_length=max_length,
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
