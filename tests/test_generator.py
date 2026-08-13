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
        length=20,
        upper=3,
        lower=3,
        digits=3,
        specials=3,
        mask=0,
    )
    assert len(password) == 20


def test_generate_password_quota_equals_length():
    password = generate_password(
        "user1",
        "resource1",
        "secret1",
        length=10,
        upper=3,
        lower=3,
        digits=2,
        specials=2,
        mask=0,
    )
    assert len(password) == 10


def test_generate_password_zero_quotas_filled_with_lower():
    password = generate_password(
        "user1",
        "resource1",
        "secret1",
        length=10,
        upper=0,
        lower=0,
        digits=0,
        specials=0,
        mask=0,
    )
    assert len(password) == 10
    assert password.islower()
    assert password.isalpha()


def test_generate_password_invalid_constraints():
    with pytest.raises(ValueError):
        generate_password(
            "user1",
            "resource1",
            "secret1",
            length=5,
        )


def test_generate_password_mask_exceeds_specials_fails():
    with pytest.raises(ValueError):
        generate_password(
            "user1",
            "resource1",
            "secret1",
            length=16,
            upper=0,
            lower=0,
            digits=0,
            specials=1,
            mask=2,
        )


def test_generate_password_from_request_matches_api():
    constraints = PasswordConstraints(18, 2, 2, 1, 1, 0)
    profile = PasswordProfile("userX", "resourceX", constraints)
    request = PasswordGenerationRequest(profile, "secretX")

    via_request = generate_password_from_request(request)
    via_kwargs = generate_password(
        "userX",
        "resourceX",
        "secretX",
        length=18,
        upper=2,
        lower=2,
        digits=1,
        specials=1,
        mask=0,
    )

    assert via_request == via_kwargs


def test_generate_password_different_versions_produce_different_results():
    pw_v1 = generate_password("user1", "resource1", "secret1", generation_version=1)
    pw_v2 = generate_password("user1", "resource1", "secret1", generation_version=2)

    assert pw_v1 != pw_v2


def test_generate_password_consistency_with_custom_version():
    pw1 = generate_password("user1", "resource1", "secret1", generation_version=3)
    pw2 = generate_password("user1", "resource1", "secret1", generation_version=3)
    assert pw1 == pw2
