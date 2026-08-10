import subprocess
from pathlib import Path

import pytest

from app.sync_service import SyncError, SyncService


def _init_git_repo(repo_path: Path, branch: str = "main") -> str:
    repo_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "-C", str(repo_path), "init", "-b", branch],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_path), "config", "user.email", "test@test.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_path), "config", "user.name", "Test"],
        check=True,
    )
    return branch


def _init_bare_remote(remote_path: Path, branch: str = "main") -> None:
    remote_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "-C", str(remote_path), "init", "--bare", "-b", branch],
        check=True,
        capture_output=True,
        text=True,
    )


def _add_commit(repo_path: Path, filename: str, content: str, message: str):
    file_path = repo_path / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    subprocess.run(
        ["git", "-C", str(repo_path), "add", "-A"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_path), "commit", "-m", message],
        check=True,
        capture_output=True,
        text=True,
    )


def _setup_repo_with_remote(tmp_path: Path, branch: str = "main"):
    local = tmp_path / "local"
    remote = tmp_path / "remote.git"

    _init_git_repo(local, branch)
    _init_bare_remote(remote, branch)

    subprocess.run(
        ["git", "-C", str(local), "remote", "add", "origin", str(remote)],
        check=True,
        capture_output=True,
        text=True,
    )

    _add_commit(local, "README.md", "# test", "initial commit")
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

    return local, remote, branch


class TestSyncService:
    def test_sync_already_up_to_date(self, tmp_path):
        local, _remote, _branch = _setup_repo_with_remote(tmp_path)

        svc = SyncService(local)
        result = svc.sync()

        assert result == "Already up to date."

    def test_sync_with_uncommitted_changes(self, tmp_path):
        local, _remote, _branch = _setup_repo_with_remote(tmp_path)

        profiles_dir = local / "profiles" / "ab"
        profiles_dir.mkdir(parents=True)
        (profiles_dir / "test.json").write_text('{"test": true}\n')

        svc = SyncService(local)
        result = svc.sync("sync: create profile user/example.com")

        assert "Synced successfully" in result

    def test_sync_with_unpushed_commits(self, tmp_path):
        local, _remote, _branch = _setup_repo_with_remote(tmp_path)

        _add_commit(local, "profiles/test.json", "{}", "add profile")

        svc = SyncService(local)
        result = svc.sync()

        assert "Synced successfully" in result

    def test_sync_not_a_git_repo(self, tmp_path):
        not_repo = tmp_path / "not_repo"
        not_repo.mkdir()

        with pytest.raises(SyncError, match="not a git repository"):
            SyncService(not_repo)

    def test_sync_no_origin_remote(self, tmp_path):
        repo = tmp_path / "repo"
        _init_git_repo(repo)

        with pytest.raises(SyncError, match="No 'origin' remote"):
            SyncService(repo)

    def test_sync_conflict_detected(self, tmp_path):
        local, remote, branch = _setup_repo_with_remote(tmp_path)

        other = tmp_path / "other"
        subprocess.run(
            ["git", "clone", str(remote), str(other)],
            check=True,
            capture_output=True,
            text=True,
        )

        (other / "README.md").write_text("# remote change\n")
        subprocess.run(
            ["git", "-C", str(other), "add", "-A"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(other), "commit", "-m", "remote change"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(other), "push", "origin", branch],
            check=True,
            capture_output=True,
            text=True,
        )

        (local / "README.md").write_text("# local change\n")
        subprocess.run(
            ["git", "-C", str(local), "add", "-A"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(local), "commit", "-m", "local change"],
            check=True,
            capture_output=True,
            text=True,
        )

        svc = SyncService(local)
        with pytest.raises(SyncError, match="Conflict rebasing"):
            svc.sync()

    def test_sync_conflict_shows_resolution_info(self, tmp_path):
        local, remote, branch = _setup_repo_with_remote(tmp_path)

        other = tmp_path / "other"
        subprocess.run(
            ["git", "clone", str(remote), str(other)],
            check=True,
            capture_output=True,
            text=True,
        )

        (other / "README.md").write_text("# remote change\n")
        subprocess.run(
            ["git", "-C", str(other), "add", "-A"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(other), "commit", "-m", "remote change"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(other), "push", "origin", branch],
            check=True,
            capture_output=True,
            text=True,
        )

        (local / "README.md").write_text("# local change\n")
        subprocess.run(
            ["git", "-C", str(local), "add", "-A"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(local), "commit", "-m", "local change"],
            check=True,
            capture_output=True,
            text=True,
        )

        svc = SyncService(local)
        try:
            svc.sync()
        except SyncError as exc:
            assert exc.conflict_info is not None
            assert "To resolve manually:" in exc.conflict_info
            assert "git rebase --continue" in exc.conflict_info
            assert "git rebase --abort" in exc.conflict_info

    def test_sync_pulls_when_no_local_changes(self, tmp_path):
        local, remote, branch = _setup_repo_with_remote(tmp_path)

        other = tmp_path / "other"
        subprocess.run(
            ["git", "clone", str(remote), str(other)],
            check=True,
            capture_output=True,
            text=True,
        )
        _add_commit(other, "new_file.txt", "remote content", "remote commit")
        subprocess.run(
            ["git", "-C", str(other), "push", "origin", branch],
            check=True,
            capture_output=True,
            text=True,
        )

        svc = SyncService(local)
        result = svc.sync()

        assert "Pulled 1 commit" in result

    def test_sync_with_master_branch(self, tmp_path):
        local, _remote, _branch = _setup_repo_with_remote(tmp_path, branch="master")

        svc = SyncService(local)
        result = svc.sync()

        assert "Already up to date." in result
