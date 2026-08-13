from app.models import PasswordConstraints, PasswordGenerationRequest, PasswordProfile


def test_password_profile_identity_pair():
    constraints = PasswordConstraints(24, 0, 0, 0, 0, 0)
    profile = PasswordProfile("userA", "resourceA", constraints)

    assert profile.identity == ("userA", "resourceA")


def test_generation_request_keeps_secret_transient():
    constraints = PasswordConstraints(16, 1, 1, 1, 1, 0)
    profile = PasswordProfile("userB", "resourceB", constraints)
    request = PasswordGenerationRequest(profile, "sec")

    assert not hasattr(profile, "secret")
    assert request.identity == profile.identity
    assert request.secret == "sec"


def test_profile_generation_version_defaults_to_1():
    constraints = PasswordConstraints(24, 0, 0, 0, 0, 0)
    profile = PasswordProfile("userC", "resourceC", constraints)

    assert profile.generation_version == 1


def test_profile_custom_generation_version():
    constraints = PasswordConstraints(24, 0, 0, 0, 0, 0)
    profile = PasswordProfile("userD", "resourceD", constraints, generation_version=5)

    assert profile.generation_version == 5
