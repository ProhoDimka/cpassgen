from click.testing import CliRunner

from app.main import generate


def test_generate_password_consistency_default_cli():
    runner = CliRunner()
    result1 = runner.invoke(generate, input="user1\nresource1\nsecret1\n")
    result2 = runner.invoke(generate, input="user1\nresource1\nsecret1\n")

    assert result1.exit_code == 0
    assert result2.exit_code == 0
    assert result1.output == result2.output


def test_generate_password_custom_options_cli():
    runner = CliRunner()
    result = runner.invoke(
        generate,
        args=[
            "--username",
            "user1",
            "--resource",
            "resource1",
            "--secret",
            "secret1",
            "--min-length",
            "8",
            "--max-length",
            "8",
            "--upper",
            "2",
            "--lower",
            "2",
            "--digits",
            "2",
            "--specials",
            "2",
            "--mask",
            "0",
        ],
    )

    assert result.exit_code == 0
    assert len(result.output.strip()) == 8
