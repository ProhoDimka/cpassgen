"""Validation helpers for CLI arguments."""

from app.models import PasswordConstraints


def validate_constraints(
    constraints: PasswordConstraints,
) -> PasswordConstraints:
    if constraints.length <= 0:
        raise ValueError("length must be positive.")
    for name, value in (
        ("upper", constraints.upper),
        ("lower", constraints.lower),
        ("digits", constraints.digits),
        ("specials", constraints.specials),
        ("mask", constraints.mask),
    ):
        if value < 0:
            raise ValueError(f"{name} must be non-negative.")
    if constraints.mask > constraints.specials:
        raise ValueError("mask must be <= specials.")

    total = (
        constraints.upper
        + constraints.lower
        + constraints.digits
        + constraints.specials
        + constraints.mask
    )
    if total > constraints.length:
        raise ValueError("Character quotas sum exceeds length.")

    return constraints
