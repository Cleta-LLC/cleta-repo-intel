from __future__ import annotations

from .models import ReleaseSnapshot


def _label(value: str) -> str:
    return value.replace("_", " ").title()


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def render_markdown(snapshot: ReleaseSnapshot) -> str:
    a = snapshot.activity
    c = snapshot.changes
    s = snapshot.signals
    work = "\n".join(f"| {_label(kind)} | {count} |" for kind, count in sorted(snapshot.work_types.items())) or "| Other | 0 |"
    categories = "\n".join(f"| {_label(kind)} | {count} |" for kind, count in sorted(snapshot.file_categories.items())) or "| Source | 0 |"
    areas = "\n".join(f"| `{area.name}` | {area.files} |" for area in snapshot.areas) or "| root | 0 |"
    reasons = "\n".join(f"- {reason}" for reason in s.complexity_reasons) or "- no elevated delivery-complexity signals detected"
    warning_section = ""
    if snapshot.warnings:
        warning_section = "\n## Warnings\n\n" + "\n".join(f"- {warning}" for warning in snapshot.warnings) + "\n"
    return f"""# Repository Snapshot: {snapshot.refs.base_ref} -> {snapshot.refs.head_ref}

## Executive Summary

**{snapshot.repository}** shows a **{_label(s.footprint)} engineering footprint** with **{_label(s.delivery_complexity)} delivery complexity** across {s.surfaces_touched} repository surface(s): {a.git_commits} Git commit(s) containing {a.change_items} detected change item(s), touching {c.files_changed} files with {c.additions:,} additions and {c.deletions:,} deletions.

This is an engineering activity signal derived from Git history. It is not an estimate of hours worked or individual productivity.

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
{warning_section}"""
