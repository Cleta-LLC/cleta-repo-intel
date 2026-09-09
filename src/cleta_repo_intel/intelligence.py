from __future__ import annotations

from collections import Counter, defaultdict
import re

from .git import Commit, FileChange
from .models import EvidenceRef, Finding, Intelligence, ReworkSignal, Signals, Theme


_PREFIX = re.compile(
    r"^(?:feat|fix|test|docs|perf|refactor|chore|build|ci|security|revert)(?:\([^)]*\))?[!:]\s*",
    re.IGNORECASE,
)
_SPACE = re.compile(r"\s+")

_THEME_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Security & access control",
        ("security", "rls", "role", "policy", "permission", "grant", "auth", "access", "tenant", "authorization"),
    ),
    (
        "Workflow & product behavior",
        ("workflow", "reconciliation", "queue", "route", "buyer", "supplier", "portal", "catalog", "matching", "match"),
    ),
    (
        "Data & schema",
        ("migration", "database", "schema", "table", "column", "foreign key", "fk", "index", "unique", "sku", "alias"),
    ),
    (
        "Quality & validation",
        ("test", "cover", "assert", "validation", "contract", "smoke", "regression"),
    ),
    (
        "Localization & UX",
        ("localize", "localization", "locale", "i18n", "translation", "navigation", "menu", "ui", "sign-in"),
    ),
    (
        "Performance",
        ("perf", "performance", "latency", "cache", "index", "optimize", "throughput"),
    ),
    (
        "Release & operations",
        ("release", "rc", "version", "deploy", "deployment", "runbook", "lockfile", "changelog", "ci", "build"),
    ),
)


def _normalize(text: str) -> str:
    without_prefix = _PREFIX.sub("", text.strip().lower())
    normalized = re.sub(r"[^a-z0-9]+", " ", without_prefix)
    return _SPACE.sub(" ", normalized).strip()


def _theme_matches(text: str) -> list[str]:
    lowered = text.lower()
    return [name for name, keywords in _THEME_RULES if any(keyword in lowered for keyword in keywords)]


def _file_theme_matches(path: str) -> list[str]:
    lowered = path.lower()
    matches: list[str] = []
    if any(token in lowered for token in ("migration", "schema", "prisma", "supabase/")):
        matches.append("Data & schema")
    if any(token in lowered for token in ("test", "spec", "__tests__")):
        matches.append("Quality & validation")
    if lowered.startswith(".github/") or any(token in lowered for token in ("dockerfile", "package.json", "pyproject.toml", "lock")):
        matches.append("Release & operations")
    if any(token in lowered for token in ("i18n", "locale", "translation")):
        matches.append("Localization & UX")
    return matches


def _release_character(work_types: Counter[str], signals: Signals, theme_names: set[str]) -> str:
    if signals.database_touched and "Security & access control" in theme_names:
        return "cross-layer hardening"
    if work_types.get("fix", 0) > work_types.get("feat", 0):
        return "stabilization"
    if work_types.get("feat", 0) >= max(2, work_types.get("fix", 0) * 2):
        return "feature delivery"
    return "mixed delivery"


def build_intelligence(
    commit_items: list[tuple[Commit, list[str]]],
    file_changes: list[FileChange],
    work_types: Counter[str],
    signals: Signals,
) -> Intelligence:
    evidence: list[EvidenceRef] = []
    theme_evidence: dict[str, list[str]] = defaultdict(list)
    theme_item_counts: Counter[str] = Counter()
    item_records: list[tuple[str, str]] = []

    for commit in (commit for commit, _ in commit_items):
        evidence.append(
            EvidenceRef(
                id=f"commit:{commit.sha[:12]}",
                kind="commit",
                label=commit.subject,
                locator=commit.sha,
                detail=f"{commit.author} at {commit.timestamp}",
            )
        )

    item_index = 0
    for commit, items in commit_items:
        for item in items:
            item_index += 1
            evidence_id = f"change:{item_index}"
            evidence.append(
                EvidenceRef(
                    id=evidence_id,
                    kind="change_item",
                    label=item,
                    locator=commit.sha,
                    detail=f"reconstructed from commit {commit.sha[:12]}",
                )
            )
            item_records.append((evidence_id, item))
            matches = _theme_matches(item)
            if item.lower().startswith("test") and "Quality & validation" not in matches:
                matches.append("Quality & validation")
            for theme in matches:
                theme_item_counts[theme] += 1
                theme_evidence[theme].append(evidence_id)

    for index, change in enumerate(file_changes, start=1):
        evidence_id = f"file:{index}"
        evidence.append(
            EvidenceRef(
                id=evidence_id,
                kind="file",
                label=change.path,
                locator=change.path,
                detail=f"+{change.additions}/-{change.deletions}",
            )
        )
        for theme in _file_theme_matches(change.path):
            theme_evidence[theme].append(evidence_id)

    theme_order = {name: index for index, (name, _) in enumerate(_THEME_RULES)}
    themes = [
        Theme(name=name, change_items=theme_item_counts.get(name, 0), evidence_ids=list(dict.fromkeys(ids)))
        for name, ids in theme_evidence.items()
        if ids
    ]
    priority = {
        "Security & access control": 1.5,
        "Workflow & product behavior": 1.0,
        "Data & schema": 1.2,
        "Quality & validation": 0.5,
        "Localization & UX": 0.8,
        "Performance": 0.8,
        "Release & operations": 0.2,
    }
    themes.sort(
        key=lambda theme: (-(theme.change_items * priority.get(theme.name, 1.0)), theme_order.get(theme.name, 999), theme.name)
    )
    theme_names = {theme.name for theme in themes}

    normalized_to_items: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for evidence_id, item in item_records:
        normalized = _normalize(item)
        if normalized:
            normalized_to_items[normalized].append((evidence_id, item))
    rework_signals: list[ReworkSignal] = []
    for records in normalized_to_items.values():
        if len(records) < 2:
            continue
        evidence_ids = [evidence_id for evidence_id, _ in records]
        label = records[0][1]
        rework_signals.append(
            ReworkSignal(
                kind="repeated_change_item",
                label=label,
                count=len(records),
                evidence_ids=evidence_ids,
            )
        )
    rework_signals.sort(key=lambda signal: (-signal.count, signal.label.lower()))

    findings: list[Finding] = []
    themes_by_name = {theme.name: theme for theme in themes}
    security_evidence = themes_by_name.get("Security & access control", Theme("", 0, [])).evidence_ids
    data_evidence = themes_by_name.get("Data & schema", Theme("", 0, [])).evidence_ids
    quality_evidence = themes_by_name.get("Quality & validation", Theme("", 0, [])).evidence_ids

    if signals.database_touched and security_evidence:
        findings.append(
            Finding(
                id="security-data-boundary",
                kind="risk",
                level="high",
                title="Security-sensitive data boundary changed",
                summary="Database/schema changes overlap with access-control or authorization semantics. Review migration ordering, role/RLS boundaries, and rollback behavior before promotion.",
                confidence="high",
                evidence_ids=list(dict.fromkeys((security_evidence + data_evidence)[:10])),
            )
        )
    if signals.surfaces_touched >= 4:
        findings.append(
            Finding(
                id="cross-layer-change",
                kind="scope",
                level="medium",
                title="Cross-layer release",
                summary=f"The release spans {signals.surfaces_touched} repository surfaces, so validation should follow the end-to-end workflow rather than isolated file changes.",
                confidence="high",
                evidence_ids=[e.id for e in evidence if e.kind == "file"][:8],
            )
        )
    if signals.tests_touched:
        findings.append(
            Finding(
                id="validation-changed",
                kind="assurance",
                level="positive",
                title="Validation changed with implementation",
                summary="Tests changed in the same release. This is evidence of validation activity, but not proof that all changed behavior is covered.",
                confidence="high",
                evidence_ids=quality_evidence[:8],
            )
        )
    if rework_signals:
        top = rework_signals[0]
        findings.append(
            Finding(
                id="repeated-correction",
                kind="process",
                level="medium",
                title="Repeated correction signal",
                summary=f"A reconstructed change item appears {top.count} times. Treat this as evidence of repeated iteration or release correction, not as an estimate of effort or time.",
                confidence="high",
                evidence_ids=top.evidence_ids,
            )
        )
    if signals.history_shape == "squash_like":
        findings.append(
            Finding(
                id="squash-compression",
                kind="evidence",
                level="info",
                title="Squash merge compresses visible history",
                summary="Commit count and active days understate the underlying iteration. Reconstructed change items are more representative for release-level analysis.",
                confidence="high",
                evidence_ids=[e.id for e in evidence if e.kind == "commit"][:4],
            )
        )

    release_character = _release_character(work_types, signals, theme_names)
    story_themes = [
        theme.name
        for theme in themes
        if theme.change_items > 0 and theme.name not in {"Quality & validation", "Release & operations"}
    ]
    dominant = (story_themes or [theme.name for theme in themes if theme.change_items > 0])[:3]
    if dominant:
        if len(dominant) == 1:
            theme_text = dominant[0]
        else:
            theme_text = ", ".join(dominant[:-1]) + f", and {dominant[-1]}"
        narrative = f"This is primarily a {release_character} release centered on {theme_text}."
    else:
        narrative = f"This is primarily a {release_character} release spanning {signals.surfaces_touched} repository surfaces."
    if signals.database_touched and security_evidence:
        narrative += " The release changes security-sensitive data boundaries, which raises promotion and rollback risk."
    if signals.tests_touched:
        narrative += " Validation artifacts changed alongside implementation."
    if rework_signals:
        narrative += f" Repeated change-item evidence shows at least one correction loop ({rework_signals[0].count} repeated entries)."

    return Intelligence(
        release_character=release_character,
        narrative=narrative,
        themes=themes,
        findings=findings,
        rework_signals=rework_signals,
        evidence=evidence,
    )
