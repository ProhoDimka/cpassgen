"""Domain models describing password generation inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class PasswordConstraints:
    """Immutable limits that control generated password shape."""

    min_length: int
    max_length: int
    upper: int
    lower: int
    digits: int
    specials: int
    mask: int


@dataclass(frozen=True)
class PasswordProfile:
    """Persistent profile identified by username and resource pair."""

    username: str
    resource: str
    constraints: PasswordConstraints

    @property
    def identity(self) -> Tuple[str, str]:
        """Unique key that can be used as a storage identifier."""

        return (self.username, self.resource)


@dataclass(frozen=True)
class PasswordGenerationRequest:
    """Runtime message that adds the transient secret to a profile."""

    profile: PasswordProfile
    secret: str

    @property
    def identity(self) -> Tuple[str, str]:
        return self.profile.identity
