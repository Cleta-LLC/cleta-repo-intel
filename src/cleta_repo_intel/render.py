from __future__ import annotations

from .models import ReleaseSnapshot


def _label(value: str) -> str:
    return value.replace("_", " ").title()


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _evidence_labels(snapshot: ReleaseSnapshot, evidence_ids: list[str], limit: int = 5) -> str:
    evidence_by_id = {evidence.id: evidence for evidence in snapshot.intelligence.evidence}
    labels = [evidence_by_id[evidence_id].label for evidence_id in evidence_ids if evidence_id in evidence_by_id]
    if not labels:
        return "n/a"
    shown = labels[:limit]
    suffix = f" (+{len(labels) - limit} more)" if len(labels) > limit else ""
    return "; ".join(f"`{label}`" for label in shown) + suffix


def render_markdown(snapshot: ReleaseSnapshot) -> str:
    a = snapshot.activity
    c = snapshot.changes
    s = snapshot.signals
    intel = snapshot.intelligence
    work = "\n".join(f"| {_label(kind)} | {count} |" for kind, count in sorted(snapshot.work_types.items())) or "| Other | 0 |"
    categories = "\n".join(f"| {_label(kind)} | {count} |" for kind, count in sorted(snapshot.file_categories.items())) or "| Source | 0 |"
    areas = "\n".join(f"| `{area.name}` | {area.files} |" for area in snapshot.areas) or "| root | 0 |"
    reasons = "\n".join(f"- {reason}" for reason in s.complexity_reasons) or "- no elevated delivery-complexity signals detected"
    themes = "\n".join(
        f"| {theme.name} | {theme.change_items} | {_evidence_labels(snapshot, theme.evidence_ids, 3)} |"
        for theme in intel.themes
    ) or "| General changes | 0 | n/a |"
    findings = "\n\n".join(
        f"### [{finding.level.upper()}] {finding.title}\n\n{finding.summary}\n\nEvidence: {_evidence_labels(snapshot, finding.evidence_ids)}\n\nConfidence: **{finding.confidence}**"
        for finding in intel.findings
    ) or "No elevated findings detected from the available Git evidence."
    rework = "\n".join(
        f"- **{signal.count}x** `{signal.label}` - evidence: {_evidence_labels(snapshot, signal.evidence_ids, 3)}"
        for signal in intel.rework_signals
    ) or "- No repeated change-item signals detected."
    warning_section = ""
    if snapshot.warnings:
        warning_section = "\n## Warnings\n\n" + "\n".join(f"- {warning}" for warning in snapshot.warnings) + "\n"
    return f"""# Repository Snapshot: {snapshot.refs.base_ref} -> {snapshot.refs.head_ref}

## Executive Summary

**{snapshot.repository}** shows a **{_label(s.footprint)} engineering footprint** with **{_label(s.delivery_complexity)} delivery complexity** across {s.surfaces_touched} repository surface(s): {a.git_commits} Git commit(s) containing {a.change_items} detected change item(s), touching {c.files_changed} files with {c.additions:,} additions and {c.deletions:,} deletions.

**Release character:** {_label(intel.release_character)}.

{intel.narrative}

This is an engineering activity signal derived from repository evidence. It is not an estimate of hours worked or individual productivity.

## Release Intelligence

### Primary Themes

Themes can overlap when the same evidence affects more than one delivery concern.

| Theme | Change items | Example evidence |
| --- | ---: | --- |
{themes}

### Findings

{findings}

### Rework / Iteration Signals

{rework}

## Delivery Profile

| Signal | Value |
| --- | --- |
| Engineering footprint | {_label(s.footprint)} |
| Delivery complexity | {_label(s.delivery_complexity)} |
| Repository surfaces touched | {s.surfaces_touched} |
| History shape | {_label(s.history_shape)} |
| Tests touched | {_yes_no(s.tests_touched)} |
| Documentation touched | {_yes_no(s.docs_touched)} |
| Database/schema touched | {_yes_no(s.database_touched)} |
| CI/configuration touched | {_yes_no(s.ci_or_config_touched)} |

### Why delivery complexity is {_label(s.delivery_complexity)}

{reasons}

## Engineering Footprint

| Metric | Value |
| --- | ---: |
| Git commits | {a.git_commits} |
| Detected change items | {a.change_items} |
| Contributors | {a.contributors} |
| Active days in visible Git history | {a.active_days} |
| Files changed | {c.files_changed} |
| Additions | {c.additions:,} |
| Deletions | {c.deletions:,} |
| Churn | {c.churn:,} |

## Work Composition

| Commit type | Count |
| --- | ---: |
{work}

## File Surface

| Category | Files |
| --- | ---: |
{categories}

## Major Areas Changed

| Area | Files |
| --- | ---: |
{areas}

## Evidence

- Base: `{snapshot.refs.base_ref}` -> `{snapshot.refs.base_sha}`
- Head: `{snapshot.refs.head_ref}` -> `{snapshot.refs.head_sha}`
- First commit in range: `{a.first_commit_at or 'n/a'}`
- Last commit in range: `{a.last_commit_at or 'n/a'}`
- Evidence records: `{len(intel.evidence)}`
{warning_section}"""
