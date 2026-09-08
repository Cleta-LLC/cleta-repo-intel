from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


class GitError(RuntimeError):
    pass


@dataclass(frozen=True)
class Commit:
    sha: str
    author: str
    timestamp: str
    message: str

    @property
    def subject(self) -> str:
        return self.message.splitlines()[0] if self.message else ""


@dataclass(frozen=True)
class FileChange:
    path: str
    additions: int
    deletions: int


def _run(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise GitError(message)
    return result.stdout


def ensure_repository(repo: Path) -> Path:
    resolved = repo.expanduser().resolve()
    if not resolved.exists():
        raise GitError(f"repository path does not exist: {resolved}")
    _run(resolved, "rev-parse", "--is-inside-work-tree")
    return Path(_run(resolved, "rev-parse", "--show-toplevel").strip())


def resolve_ref(repo: Path, ref: str) -> str:
    return _run(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").strip()


def collect_commits(repo: Path, base_ref: str, head_ref: str) -> list[Commit]:
    raw = _run(
        repo,
        "log",
        "--reverse",
        "--format=%H%x1f%aN%x1f%aI%x1f%B%x1e",
        f"{base_ref}..{head_ref}",
    )
    commits: list[Commit] = []
    for record in raw.split("\x1e"):
        record = record.strip()
        if not record:
            continue
        parts = record.split("\x1f", 3)
        if len(parts) == 4:
            sha, author, timestamp, message = parts
            commits.append(Commit(sha, author, timestamp, message.strip()))
    return commits


def collect_file_changes(repo: Path, base_ref: str, head_ref: str) -> list[FileChange]:
    raw = _run(repo, "diff", "--numstat", "--find-renames", base_ref, head_ref)
    changes: list[FileChange] = []
    for line in raw.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        changes.append(
            FileChange(
                path,
                int(added) if added.isdigit() else 0,
                int(deleted) if deleted.isdigit() else 0,
            )
        )
    return changes
