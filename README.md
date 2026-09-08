# cleta-repo-intel

Standalone, local-first repository intelligence for Cleta-managed codebases.

The first capability is a release snapshot: compare two Git refs and produce an evidence-backed Markdown and JSON report describing both the **engineering footprint** and **delivery complexity** of the range.

It deliberately does **not** convert Git activity into hours worked or individual productivity.

## v0.1 scope

- local Git repository input
- Python 3.12+
- standard library at runtime
- no GitHub API requirement
- no database
- no LLM
- no repository writes
- Markdown + JSON output

## Install

```bash
python -m pip install -e .
```

## Use

```bash
cleta-repo snapshot /path/to/repository \
  --from v0.5.7 \
  --to v0.5.8
```

For a checked-out Encargo frontend while the next release is still on `main`:

```bash
cleta-repo snapshot /path/to/encargo-test-cleta \
  --from 8127015f3cc72ba5d1019b79273a9bd36ba82fb2 \
  --to main
```

Default output:

```text
release-reports/<head-ref>/report.json
release-reports/<head-ref>/report.md
```

## Report contents

- exact base/head refs and SHAs
- Git commits, detected conventional change items, and contributors
- active development days visible in the selected Git history
- changed files, additions, deletions, churn
- conventional commit mix
- source/test/docs/database/CI/config file surface
- largest changed repository areas
- squash-history detection so merge strategy does not silently undercount work
- deterministic engineering-footprint signal for change-set size
- deterministic delivery-complexity signal with explicit reasons such as database/schema changes, configuration changes, and cross-layer breadth

The two signals are intentionally separate: a release can have moderate code volume but high delivery complexity because it crosses security-sensitive data, schema, workflow, or deployment boundaries.

## Python API

```python
from cleta_repo_intel import analyze_release, render_markdown

report = analyze_release(
    "/path/to/repo",
    base_ref="v0.5.7",
    head_ref="v0.5.8",
)

print(render_markdown(report))
```

## Roadmap

- `v0.1.0`: local Git snapshot
- `v0.2.0`: optional remote clone/fetch ingestion
- `v0.3.0`: optional GitHub PR/review/CI enrichment
- `v0.4.0`: semver history and consecutive snapshots
- `v0.5.0`: autodocs/agent consumers if the reports prove useful

The target repositories should not need to vendor this code. They are inputs, not hosts.
