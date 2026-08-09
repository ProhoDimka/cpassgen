import pytest
from app.generator import generate_password, generate_password_from_request
from app.models import PasswordConstraints, PasswordGenerationRequest, PasswordProfile


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


def test_generate_password_from_request_matches_api():
    constraints = PasswordConstraints(14, 18, 2, 2, 1, 1, 0)
    profile = PasswordProfile("userX", "resourceX", constraints)
    request = PasswordGenerationRequest(profile, "secretX")

    via_request = generate_password_from_request(request)
    via_kwargs = generate_password(
        "userX",
        "resourceX",
        "secretX",
        min_length=14,
        max_length=18,
        upper=2,
        lower=2,
        digits=1,
        specials=1,
        mask=0,
    )

    assert via_request == via_kwargs
