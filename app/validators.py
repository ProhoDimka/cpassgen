"""Validation helpers for CLI arguments."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordConstraints:
    min_length: int
    max_length: int
    upper: int
    lower: int
    digits: int
    specials: int
    mask: int


def validate_constraints(
    constraints: PasswordConstraints,
) -> PasswordConstraints:
    if constraints.min_length <= 0:
        raise ValueError("min_length must be positive.")
    if constraints.max_length < constraints.min_length:
        raise ValueError("max_length must be >= min_length.")
    if constraints.mask < 0:
        raise ValueError("mask must be non-negative.")

    typed_sum = (
        constraints.upper
        + constraints.lower
        + constraints.digits
        + constraints.specials
    )
    if typed_sum > constraints.max_length:
        raise ValueError("Character quotas sum exceeds max_length.")

    return constraints
