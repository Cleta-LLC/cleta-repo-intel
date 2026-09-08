from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from .analyze import analyze_release
from .git import GitError
from .render import render_markdown


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return cleaned or "snapshot"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cleta-repo")
    subparsers = parser.add_subparsers(dest="command", required=True)
    snapshot = subparsers.add_parser("snapshot", help="analyze repository activity between two Git refs")
    snapshot.add_argument("repository", nargs="?", default=".", help="local Git repository path")
    snapshot.add_argument("--from", dest="base_ref", required=True, help="base Git ref")
    snapshot.add_argument("--to", dest="head_ref", default="HEAD", help="head Git ref (default: HEAD)")
    snapshot.add_argument("--output", type=Path, default=Path("release-reports"), help="output directory")
    snapshot.add_argument("--format", choices=("both", "json", "markdown"), default="both")
    return parser


def _snapshot(args: argparse.Namespace) -> int:
    report = analyze_release(args.repository, args.base_ref, args.head_ref)
    output_dir = args.output / _safe_name(args.head_ref)
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.format in {"both", "json"}:
        json_path = output_dir / "report.json"
        json_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
        print(json_path)
    if args.format in {"both", "markdown"}:
        md_path = output_dir / "report.md"
        md_path.write_text(render_markdown(report), encoding="utf-8")
        print(md_path)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            return _snapshot(args)
    except GitError as exc:
        print(f"cleta-repo: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
