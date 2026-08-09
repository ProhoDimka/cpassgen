from click.testing import CliRunner
from app.main import generate

def test_generate_password_consistency():
    runner = CliRunner()
    result1 = runner.invoke(generate, input="user1\nresource1\nsecret1\n")
    result2 = runner.invoke(generate, input="user1\nresource1\nsecret1\n")

    assert result1.exit_code == 0
    assert result2.exit_code == 0
    assert result1.output == result2.output
