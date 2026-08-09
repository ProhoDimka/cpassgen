import pytest
from app.generator import generate_password


def test_generate_password_consistency_default():
    pw1 = generate_password("user1", "resource1", "secret1")
    pw2 = generate_password("user1", "resource1", "secret1")
    assert pw1 == pw2


def test_generate_password_custom_length():
    password = generate_password(
        "user1",
        "resource1",
        "secret1",
        min_length=20,
        max_length=20,
        upper=3,
        lower=3,
        digits=3,
        specials=3,
    )
    assert len(password) == 20


def test_generate_password_quota_equals_length():
    password = generate_password(
        "user1",
        "resource1",
        "secret1",
        min_length=10,
        max_length=10,
        upper=3,
        lower=3,
        digits=2,
        specials=2,
    )
    assert len(password) == 10


def test_generate_password_invalid_constraints():
    with pytest.raises(ValueError):
        generate_password(
            "user1",
            "resource1",
            "secret1",
            min_length=5,
            max_length=4,
        )
