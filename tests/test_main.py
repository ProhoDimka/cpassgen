import subprocess

from click.testing import CliRunner

from app.main import cli


def _setup_git_repo_with_remote(tmp_path, branch="main"):
    local = tmp_path / "local"
    remote = tmp_path / "remote.git"
    local.mkdir(parents=True, exist_ok=True)
    remote.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["git", "-C", str(local), "init", "-b", branch],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "-C", str(local), "config", "user.email", "test@test.com"],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "-C", str(local), "config", "user.name", "Test"],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "-C", str(remote), "init", "--bare", "-b", branch],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "-C", str(local), "remote", "add", "origin", str(remote)],
        check=True, capture_output=True, text=True,
    )

    (local / "README.md").write_text("# test")
    subprocess.run(
        ["git", "-C", str(local), "add", "-A"],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "-C", str(local), "commit", "-m", "initial"],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "-C", str(local), "push", "-u", "origin", branch],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "-C", str(local), "remote", "set-head", "origin", branch],
        check=True, capture_output=True, text=True,
    )

    return local


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
    result2 = runner.invoke(
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
            "--generation-version",
            "2",
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
        args=[
            "get",
            "--username",
            "missing",
            "--resource",
            "resource",
            "--secret",
            "secret",
        ],
        env={"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)},
    )

    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_create_with_custom_generation_version(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    result = runner.invoke(
        cli,
        args=[
            "create",
            "--username",
            "user1",
            "--resource",
            "resource1",
            "--generation-version",
            "3",
        ],
        env=env,
    )

    assert result.exit_code == 0
    assert "Profile created." in result.output


def test_set_constraints_without_version_bump_fails(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    runner.invoke(
        cli,
        args=["create", "--username", "user1", "--resource", "resource1"],
        env=env,
    )
    result = runner.invoke(
        cli,
        args=[
            "set",
            "--username",
            "user1",
            "--resource",
            "resource1",
            "--min-length",
            "20",
            "--max-length",
            "20",
        ],
        env=env,
    )

    assert result.exit_code == 1
    assert "generation_version" in result.output


def test_generate_password_respects_version_from_profile(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    runner.invoke(
        cli,
        args=[
            "create",
            "--username",
            "user1",
            "--resource",
            "resource1",
            "--generation-version",
            "5",
        ],
        env=env,
    )
    pw1 = runner.invoke(
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
    pw2 = runner.invoke(
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

    assert pw1.exit_code == 0
    assert pw2.exit_code == 0
    assert pw1.output == pw2.output


def test_sync_fails_when_not_git_repo(tmp_path):
    runner = CliRunner()
    not_repo = tmp_path / "not_repo"
    not_repo.mkdir()

    result = runner.invoke(
        cli,
        args=["sync"],
        env={"PASS_GEN_GIT_PERSISTENCE_PATH": str(not_repo)},
    )

    assert result.exit_code == 1
    assert "not a git repository" in result.output


def test_create_does_not_prompt_sync_in_non_tty(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    result = runner.invoke(
        cli,
        args=["create", "--username", "user1", "--resource", "resource1"],
        env=env,
    )

    assert result.exit_code == 0
    assert "Profile created." in result.output


def test_sync_cli_succeeds_up_to_date(tmp_path):
    repo = _setup_git_repo_with_remote(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        args=["sync"],
        env={"PASS_GEN_GIT_PERSISTENCE_PATH": str(repo)},
    )

    assert result.exit_code == 0
    assert "Already up to date." in result.output
