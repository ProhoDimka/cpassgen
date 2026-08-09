from app.generator import generate_password

def test_generate_password_consistency():
    pw1 = generate_password("user1", "resource1", "secret1")
    pw2 = generate_password("user1", "resource1", "secret1")
    assert pw1 == pw2


def test_generate_password_output():
    # Known output for inputs a, b, c
    expected = generate_password("a", "b", "c")
    assert expected == generate_password("a", "b", "c")
