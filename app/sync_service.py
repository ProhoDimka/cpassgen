"""Git synchronization service for password profile storage."""

from __future__ import annotations

import subprocess  # nosec B404
from pathlib import Path


class SyncError(Exception):
    """Raised when git sync operations fail."""

    def __init__(self, message: str, conflict_info: str | None = None):
        super().__init__(message)
        self.conflict_info = conflict_info


class SyncService:
    """Synchronize profile storage with a remote git repository."""

    def __init__(self, repo_path: Path):
        self._repo = repo_path
        self._ensure_git_repo()

    def _git(self, *args: str, check: bool = True):
        return subprocess.run(  # nosec B603 B607
            ["git", *args],
            cwd=self._repo,
            capture_output=True,
            text=True,
            check=check,
        )

    def _ensure_git_repo(self) -> None:
        result = self._git("rev-parse", "--git-dir", check=False)
        if result.returncode != 0:
            raise SyncError(
                f"'{self._repo}' is not a git repository. "
                "Initialize it with 'git init' before syncing."
            )
        result = self._git("remote", "get-url", "origin", check=False)
        if result.returncode != 0:
            raise SyncError(
                f"No 'origin' remote configured in '{self._repo}'. "
                "Add one with 'git remote add origin <url>'."
            )

    def _default_branch(self) -> str:
        ref = "refs/remotes/origin/HEAD"
        result = self._git("symbolic-ref", ref, check=False)
        if result.returncode == 0:
            ref = result.stdout.strip()
            return ref.rsplit("/", 1)[-1]
        for candidate in ("main", "master"):
            result = self._git(
                "show-ref",
                "--verify",
                f"refs/remotes/origin/{candidate}",
                check=False,
            )
            if result.returncode == 0:
                return candidate
        raise SyncError(
            "Could not determine the default branch of remote 'origin'. "
            "Make sure the remote is reachable and has at least one branch."
        )

    def _working_tree_dirty(self) -> bool:
        result = self._git("status", "--porcelain", check=False)
        return bool(result.stdout.strip())

    def _count_ahead(self, branch: str) -> int:
        result = self._git(
            "rev-list",
            "--count",
            f"origin/{branch}..HEAD",
            check=False,
        )
        try:
            return int(result.stdout.strip())
        except ValueError:
            return 0

    def _count_behind(self, branch: str) -> int:
        result = self._git(
            "rev-list",
            "--count",
            f"HEAD..origin/{branch}",
            check=False,
        )
        try:
            return int(result.stdout.strip())
        except ValueError:
            return 0

    def sync(self, commit_message: str | None = None) -> str:
        branch = self._default_branch()

        self._git("fetch", "origin", branch)

        dirty = self._working_tree_dirty()
        ahead = self._count_ahead(branch)
        behind = self._count_behind(branch)

        if not dirty and ahead == 0:
            if behind == 0:
                return "Already up to date."
            self._git("pull", "--ff-only", "origin", branch)
            return f"Pulled {behind} commit(s) from origin/{branch}."

        if dirty:
            msg = commit_message or "sync: update password profiles"
            self._git("add", "-A")
            self._git("commit", "-m", msg)

        if behind > 0:
            result = self._git("rebase", f"origin/{branch}", check=False)
            if result.returncode != 0:
                self._git("rebase", "--abort", check=False)
                err = result.stderr.strip()
                msg = f"Conflict rebasing onto origin/{branch}."
                raise SyncError(
                    msg,
                    conflict_info=(
                        f"Your local changes conflict with remote "
                        f"changes.\n\n"
                        f"To resolve manually:\n"
                        f"  1. cd {self._repo}\n"
                        f"  2. git status  # see conflicted files\n"
                        f"  3. # Edit each conflicted file, then:\n"
                        f"  4. git add <file>  # mark as resolved\n"
                        f"  5. git rebase --continue\n"
                        f"  6. git push origin {branch}\n"
                        f"\nTo abort and discard local changes:\n"
                        f"  git rebase --abort\n"
                        f"  git reset --hard origin/{branch}\n"
                        f"\nGit error:\n{err}"
                    ),
                )

        self._git("push", "origin", branch)
        return f"Synced successfully. Changes pushed to origin/{branch}."
