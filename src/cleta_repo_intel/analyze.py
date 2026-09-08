from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
import re

from .git import Commit, collect_commits, collect_file_changes, ensure_repository, resolve_ref
from .models import Activity, Area, Changes, RefRange, ReleaseSnapshot, Signals


_COMMIT_TYPE = re.compile(
    r"^(feat|fix|test|docs|perf|refactor|chore|build|ci|security|revert)(?:\([^)]*\))?[!:]",
    re.IGNORECASE,
)
_BULLET = re.compile(r"^[*+-]\s+")


def _commit_type(subject: str) -> str:
    match = _COMMIT_TYPE.match(subject.strip())
    return match.group(1).lower() if match else "other"


def _change_items(commit: Commit) -> list[str]:
    lines = [line.strip() for line in commit.message.splitlines()]
    subject = lines[0] if lines else ""
    body_candidates = []
    for line in lines[1:]:
        normalized = _BULLET.sub("", line).strip()
        if normalized and _COMMIT_TYPE.match(normalized):
            body_candidates.append(normalized)
    if body_candidates:
        return body_candidates
    return [subject] if subject else []


def _file_category(path: str) -> str:
    lower = path.lower()
    name = Path(lower).name
    suffix = Path(lower).suffix
    parts = set(Path(lower).parts)
    if "tests" in parts or "test" in parts or "__tests__" in parts or ".test." in name or ".spec." in name:
        return "tests"
    if "docs" in parts or name.startswith("readme") or name.startswith("changelog") or suffix == ".md":
        return "docs"
    if "migrations" in parts or "prisma" in parts or "schema" in parts or lower.startswith("supabase/migrations/"):
        return "database"
    if lower.startswith(".github/") or name.startswith("dockerfile") or "workflow" in parts:
        return "ci"
    if name in {"package.json", "pyproject.toml", "tsconfig.json", "vite.config.ts", "vite.config.js"} or name.startswith(("eslint", "prettier", "vite.config", "tsconfig")):
        return "config"
    return "source"


def _area(path: str) -> str:
    parts = Path(path).parts
    if len(parts) <= 1:
        return "root"
    first = parts[0]
    if first in {"src", "app", "packages", "supabase", "tests", "test", "docs", ".github"}:
        return f"{first}/{parts[1]}"
    return first


def _footprint(change_items: int, files: int, churn: int) -> str:
    score = 0
    score += 1 if change_items >= 6 else 0
    score += 1 if change_items >= 20 else 0
    score += 1 if files >= 15 else 0
    score += 1 if files >= 50 else 0
    score += 1 if churn >= 1500 else 0
    score += 1 if churn >= 7500 else 0
    if score <= 1:
        return "small"
    if score <= 3:
        return "medium"
    if score <= 5:
        return "large"
    return "very_large"


def analyze_release(repository: str | Path, base_ref: str, head_ref: str = "HEAD") -> ReleaseSnapshot:
    repo = ensure_repository(Path(repository))
    base_sha = resolve_ref(repo, base_ref)
    head_sha = resolve_ref(repo, head_ref)
    commits = collect_commits(repo, base_ref, head_ref)
    file_changes = collect_file_changes(repo, base_ref, head_ref)
    change_items = [item for commit in commits for item in _change_items(commit)]
    work_types = Counter(_commit_type(item) for item in change_items)
    categories = Counter(_file_category(change.path) for change in file_changes)
    areas = Counter(_area(change.path) for change in file_changes)
    additions = sum(change.additions for change in file_changes)
    deletions = sum(change.deletions for change in file_changes)
    timestamps = [datetime.fromisoformat(commit.timestamp) for commit in commits]
    active_days = len({timestamp.date() for timestamp in timestamps})
    squash_like = len(change_items) >= 6 and len(change_items) > max(len(commits) * 3, 5)
    warnings: list[str] = []
    if not commits:
        warnings.append("No commits found in the selected range.")
    if not file_changes:
        warnings.append("No changed files found in the selected range.")
    if squash_like:
        warnings.append("History appears squash-compressed: Git commit count and active days reflect merged history; change-item counts are reconstructed from conventional sub-messages.")
    return ReleaseSnapshot(
        schema_version="0.1",
        repository=repo.name,
        refs=RefRange(base_ref, base_sha, head_ref, head_sha),
        activity=Activity(
            git_commits=len(commits),
            change_items=len(change_items),
            contributors=len({commit.author for commit in commits}),
            active_days=active_days,
            first_commit_at=timestamps[0].isoformat() if timestamps else None,
            last_commit_at=timestamps[-1].isoformat() if timestamps else None,
        ),
        changes=Changes(len(file_changes), additions, deletions, additions + deletions),
        work_types=dict(sorted(work_types.items())),
        file_categories=dict(sorted(categories.items())),
        areas=[Area(name, count) for name, count in areas.most_common(10)],
        signals=Signals(
            footprint=_footprint(len(change_items), len(file_changes), additions + deletions),
            history_shape="squash_like" if squash_like else "direct",
            tests_touched=categories.get("tests", 0) > 0,
            docs_touched=categories.get("docs", 0) > 0,
            database_touched=categories.get("database", 0) > 0,
            ci_or_config_touched=(categories.get("ci", 0) + categories.get("config", 0)) > 0,
        ),
        warnings=warnings,
    )
