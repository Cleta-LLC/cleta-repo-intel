from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RefRange:
    base_ref: str
    base_sha: str
    head_ref: str
    head_sha: str


@dataclass(frozen=True)
class Activity:
    git_commits: int
    change_items: int
    contributors: int
    active_days: int
    first_commit_at: str | None
    last_commit_at: str | None


@dataclass(frozen=True)
class Changes:
    files_changed: int
    additions: int
    deletions: int
    churn: int


@dataclass(frozen=True)
class Area:
    name: str
    files: int


@dataclass(frozen=True)
class Signals:
    footprint: str
    history_shape: str
    tests_touched: bool
    docs_touched: bool
    database_touched: bool
    ci_or_config_touched: bool


@dataclass(frozen=True)
class ReleaseSnapshot:
    schema_version: str
    repository: str
    refs: RefRange
    activity: Activity
    changes: Changes
    work_types: dict[str, int]
    file_categories: dict[str, int]
    areas: list[Area]
    signals: Signals
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
