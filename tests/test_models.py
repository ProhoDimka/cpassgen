from app.models import (
    PasswordConstraints,
    PasswordGenerationRequest,
    PasswordProfile,
)


def test_password_profile_identity_pair():
    constraints = PasswordConstraints(24, 32, 0, 0, 0, 0, 0)
    profile = PasswordProfile("userA", "resourceA", constraints)

    assert profile.identity == ("userA", "resourceA")


def test_generation_request_keeps_secret_transient():
    constraints = PasswordConstraints(12, 16, 1, 1, 1, 1, 0)
    profile = PasswordProfile("userB", "resourceB", constraints)
    request = PasswordGenerationRequest(profile, "sec")

    assert not hasattr(profile, "secret")
    assert request.identity == profile.identity
    assert request.secret == "sec"
