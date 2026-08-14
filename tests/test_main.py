import json
import subprocess

from click.testing import CliRunner

from app.main import cli

CONSTRAINTS_PROMPT_INPUT = "\n" * 6


def _setup_git_repo_with_remote(tmp_path, branch="main"):
    local = tmp_path / "local"
    remote = tmp_path / "remote.git"
    local.mkdir(parents=True, exist_ok=True)
    remote.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["git", "-C", str(local), "init", "-b", branch],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(local), "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(local), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(remote), "init", "--bare", "-b", branch],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(local), "remote", "add", "origin", str(remote)],
        check=True,
        capture_output=True,
        text=True,
    )

    (local / "README.md").write_text("# test")
    subprocess.run(
        ["git", "-C", str(local), "add", "-A"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(local), "commit", "-m", "initial"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(local), "push", "-u", "origin", branch],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(local), "remote", "set-head", "origin", branch],
        check=True,
        capture_output=True,
        text=True,
    )

    return local


def test_create_then_get_password_consistency_default_cli(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    create_result = runner.invoke(
        cli,
        args=["create", "--username", "user1", "--resource", "resource1"],
        env=env,
        input=CONSTRAINTS_PROMPT_INPUT,
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


def test_bump_profile_constraints_then_get_password(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    create_result = runner.invoke(
        cli,
        args=["create", "--username", "user1", "--resource", "resource1"],
        env=env,
        input=CONSTRAINTS_PROMPT_INPUT,
    )
    bump_result = runner.invoke(
        cli,
        args=[
            "bump",
            "--username",
            "user1",
            "--resource",
            "resource1",
            "--length",
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
    assert bump_result.exit_code == 0
    assert get_result.exit_code == 0
    assert len(get_result.output.strip()) == 8


def test_bump_without_constraints_increments_version(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    runner.invoke(
        cli,
        args=["create", "--username", "user1", "--resource", "resource1"],
        env=env,
        input=CONSTRAINTS_PROMPT_INPUT,
    )
    bump_result = runner.invoke(
        cli,
        args=[
            "bump",
            "--username",
            "user1",
            "--resource",
            "resource1",
        ],
        env=env,
    )

    assert bump_result.exit_code == 0
    assert "bumped to version 2" in bump_result.output


def test_bump_records_history_when_constraints_unchanged(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    create_result = runner.invoke(
        cli,
        args=[
            "create",
            "--username",
            "user1",
            "--resource",
            "resource1",
            "--length",
            "24",
            "--upper",
            "3",
            "--digits",
            "5",
        ],
        env=env,
    )
    bump_result = runner.invoke(
        cli,
        args=["bump", "--username", "user1", "--resource", "resource1"],
        env=env,
    )

    json_files = list((tmp_path / "profiles").rglob("*.json"))
    raw = json.loads(json_files[0].read_text(encoding="utf-8"))

    assert create_result.exit_code == 0
    assert bump_result.exit_code == 0
    assert raw["generation_version"] == 2
    assert len(raw["version_history"]) == 1
    assert raw["version_history"][0]["generation_version"] == 1
    assert raw["version_history"][0]["constraints"]["digits"] == 5
    assert raw["version_history"][0]["constraints"]["upper"] == 3


def test_bump_missing_profile_fails(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    result = runner.invoke(
        cli,
        args=[
            "bump",
            "--username",
            "user1",
            "--resource",
            "resource1",
        ],
        env=env,
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
        input=CONSTRAINTS_PROMPT_INPUT,
    )

    assert result.exit_code == 0
    assert "Profile created." in result.output


def test_create_prompts_for_constraints_interactively(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    create_result = runner.invoke(
        cli,
        args=["create", "--username", "user1", "--resource", "resource1"],
        env=env,
        input="16\n2\n2\n2\n2\n0\n",
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
    assert get_result.exit_code == 0
    assert len(get_result.output.strip()) == 16


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
        input=CONSTRAINTS_PROMPT_INPUT,
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
        input=CONSTRAINTS_PROMPT_INPUT,
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


def test_create_reads_persistence_path_from_config_file(tmp_path):
    runner = CliRunner()
    profiles = tmp_path / "profiles"
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"git_persistence_path": str(profiles)}))

    result = runner.invoke(
        cli,
        args=[
            "--config",
            str(config_file),
            "create",
            "--username",
            "user1",
            "--resource",
            "resource1",
        ],
        env={},
        input=CONSTRAINTS_PROMPT_INPUT,
    )

    assert result.exit_code == 0
    assert "Profile created." in result.output
    assert (profiles / "profiles").exists()


def test_env_var_overrides_config_file_persistence_path(tmp_path):
    runner = CliRunner()
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({"git_persistence_path": str(tmp_path / "from_config")})
    )
    env_profiles = tmp_path / "env_profiles"

    result = runner.invoke(
        cli,
        args=[
            "--config",
            str(config_file),
            "create",
            "--username",
            "user1",
            "--resource",
            "resource1",
        ],
        env={"PASS_GEN_GIT_PERSISTENCE_PATH": str(env_profiles)},
        input=CONSTRAINTS_PROMPT_INPUT,
    )

    assert result.exit_code == 0
    assert (env_profiles / "profiles").exists()
    assert not (tmp_path / "from_config").exists()


def test_get_reads_secret_from_config_file(tmp_path):
    runner = CliRunner()
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "git_persistence_path": str(tmp_path),
                "key_word": "config-secret",
            }
        )
    )

    runner.invoke(
        cli,
        args=[
            "--config",
            str(config_file),
            "create",
            "--username",
            "user1",
            "--resource",
            "resource1",
        ],
        env={},
        input=CONSTRAINTS_PROMPT_INPUT,
    )
    result = runner.invoke(
        cli,
        args=[
            "--config",
            str(config_file),
            "get",
            "--username",
            "user1",
            "--resource",
            "resource1",
        ],
        env={},
    )

    assert result.exit_code == 0
    assert len(result.output.strip()) > 0


def test_get_cli_secret_overrides_config_key_word(tmp_path):
    runner = CliRunner()
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "git_persistence_path": str(tmp_path),
                "key_word": "config-secret",
            }
        )
    )

    runner.invoke(
        cli,
        args=[
            "--config",
            str(config_file),
            "create",
            "--username",
            "user1",
            "--resource",
            "resource1",
        ],
        env={},
        input=CONSTRAINTS_PROMPT_INPUT,
    )
    result = runner.invoke(
        cli,
        args=[
            "--config",
            str(config_file),
            "get",
            "--username",
            "user1",
            "--resource",
            "resource1",
            "--secret",
            "cli-secret",
        ],
        env={},
    )

    assert result.exit_code == 0
    assert result.output.strip() != ""


def test_get_missing_config_file_fails(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        args=[
            "--config",
            str(tmp_path / "missing.json"),
            "get",
            "--username",
            "user1",
            "--resource",
            "resource1",
            "--secret",
            "secret",
        ],
        env={},
    )

    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_list_empty_repo_shows_no_profiles(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        args=["list"],
        env={"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)},
    )

    assert result.exit_code == 0
    assert "No profiles found" in result.output


def test_list_shows_profiles_with_version_and_created_at(tmp_path):
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
            "3",
        ],
        env=env,
        input=CONSTRAINTS_PROMPT_INPUT,
    )

    result = runner.invoke(cli, args=["list"], env=env)

    assert result.exit_code == 0
    assert "user1@resource1" in result.output
    assert "v3" in result.output
    assert "+00:00" in result.output


def test_history_shows_current_and_past_generations(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    runner.invoke(
        cli,
        args=["create", "--username", "user1", "--resource", "resource1"],
        env=env,
        input=CONSTRAINTS_PROMPT_INPUT,
    )
    runner.invoke(
        cli,
        args=[
            "bump",
            "--username",
            "user1",
            "--resource",
            "resource1",
            "--length",
            "8",
        ],
        env=env,
    )

    result = runner.invoke(
        cli,
        args=["history", "--username", "user1", "--resource", "resource1"],
        env=env,
    )

    assert result.exit_code == 0
    assert "v2" in result.output
    assert "v1" in result.output
    assert "(current)" in result.output
    assert "length=8" in result.output
    assert "length=24" in result.output
    assert "password:" not in result.output


def test_history_with_passwords_generates_passwords(tmp_path):
    runner = CliRunner()
    env = {"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)}

    runner.invoke(
        cli,
        args=["create", "--username", "user1", "--resource", "resource1"],
        env=env,
        input=CONSTRAINTS_PROMPT_INPUT,
    )
    runner.invoke(
        cli,
        args=[
            "bump",
            "--username",
            "user1",
            "--resource",
            "resource1",
            "--length",
            "8",
        ],
        env=env,
    )

    result = runner.invoke(
        cli,
        args=[
            "history",
            "--username",
            "user1",
            "--resource",
            "resource1",
            "--with-passwords",
            "--secret",
            "secret1",
        ],
        env=env,
    )

    assert result.exit_code == 0
    password_lines = [
        line.strip()
        for line in result.output.splitlines()
        if "password:" in line
    ]
    assert len(password_lines) == 2
    assert len(password_lines[0].split("password: ")[1]) == 8
    assert len(password_lines[1].split("password: ")[1]) == 24


def test_history_missing_profile_fails(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        args=["history", "--username", "user1", "--resource", "resource1"],
        env={"PASS_GEN_GIT_PERSISTENCE_PATH": str(tmp_path)},
    )

    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_get_config_prints_non_secret_values(tmp_path):
    runner = CliRunner()
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "git_persistence_path": str(tmp_path),
                "key_word": "config-secret",
            }
        )
    )

    result = runner.invoke(
        cli,
        args=["--config", str(config_file), "get-config"],
        env={},
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output == {"git_persistence_path": str(tmp_path)}
    assert "key_word" not in output
    assert "config-secret" not in result.output
