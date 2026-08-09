from click.testing import CliRunner

from app.main import cli


def test_create_then_get_password_consistency_default_cli(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    create_result = runner.invoke(
        cli,
        args=["create", "--username", "user1", "--resource", "resource1"],
        env=env,
    )
    result1 = runner.invoke(
        cli,
        args=["get", "--username", "user1", "--resource", "resource1", "--secret", "secret1"],
        env=env,
    )
    result2 = runner.invoke(
        cli,
        args=["get", "--username", "user1", "--resource", "resource1", "--secret", "secret1"],
        env=env,
    )

    assert create_result.exit_code == 0
    assert result1.exit_code == 0
    assert result2.exit_code == 0
    assert result1.output == result2.output


def test_set_profile_constraints_then_get_password(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    create_result = runner.invoke(
        cli,
        args=["create", "--username", "user1", "--resource", "resource1"],
        env=env,
    )
    set_result = runner.invoke(
        cli,
        args=[
            "set",
            "--username",
            "user1",
            "--resource",
            "resource1",
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
        env=env,
    )
    get_result = runner.invoke(
        cli,
        args=[
            "get",
            "--username",
            "user1",
            "--resource",
            "resource1",
            "--secret",
            "secret1",
        ],
        env=env,
    )

    assert create_result.exit_code == 0
    assert set_result.exit_code == 0
    assert get_result.exit_code == 0
    assert len(get_result.output.strip()) == 8


def test_get_requires_existing_profile(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        args=["get", "--username", "missing", "--resource", "resource", "--secret", "secret"],
        env={"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)},
    )

    assert result.exit_code == 1
    assert "does not exist" in result.output
