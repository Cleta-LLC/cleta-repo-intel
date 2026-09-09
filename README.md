# cleta-repo-intel

Standalone, local-first repository intelligence for Cleta-managed codebases.

`cleta-repo` compares two Git refs and produces evidence-backed release intelligence for humans and agents. The deterministic layer owns facts; semantic interpretation is derived from those facts and always links back to repository evidence.

It deliberately does **not** convert Git activity into hours worked or individual productivity.

## Current scope

- local Git repository input
- Python 3.12+
- standard library at runtime
- no GitHub API requirement
- no database
- no LLM requirement
- no target-repository writes
- JSON, Markdown, and self-contained HTML output

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

Default output:

```text
release-reports/<head-ref>/report.json
release-reports/<head-ref>/report.md
release-reports/<head-ref>/report.html
```

Use `--format json`, `--format markdown`, or `--format html` for one artifact. `--format both` preserves the original JSON + Markdown behavior; `--format all` is the default.

## What the report knows

### Deterministic evidence

- exact base/head refs and SHAs
- Git commits and contributors
- conventional change-item reconstruction for squash-compressed histories
- changed files, additions, deletions, and churn
- source/test/docs/database/CI/config surfaces
- major repository areas
- engineering-footprint and delivery-complexity signals

### Release intelligence

- release character such as feature delivery, stabilization, or cross-layer hardening
- evidence-linked themes such as workflow/product behavior, security/access control, data/schema, validation, localization, performance, and release operations
- explicit findings with level, kind, confidence, and evidence IDs
- repeated change-item detection as a conservative rework/iteration signal
- a concise executive narrative
- a self-contained HTML report with expandable evidence

Themes can overlap because one change can affect more than one delivery concern. A test around an RLS migration, for example, is both validation evidence and security/data evidence.

## Evidence-first agent model

The report schema is designed so future agents can reason over a stable evidence layer instead of scraping prose.

```text
Git refs / commits / files
          |
          v
  deterministic snapshot
          |
          v
 evidence records + signals
          |
          v
 themes / findings / narrative
          |
     +----+-----+
     |          |
   humans     agents
 Markdown     MCP / API
 HTML         investigation
 JSON         automation
```

An LLM can later improve clustering, explanations, and investigation, but it should not be allowed to replace or fabricate the underlying evidence.

## Python API

```python
from cleta_repo_intel import analyze_release, render_html, render_markdown

report = analyze_release(
    "/path/to/repo",
    base_ref="v0.5.7",
    head_ref="v0.5.8",
)

print(render_markdown(report))
html = render_html(report)
```

## Roadmap

- `v0.1.0` - deterministic local Git release snapshot: refs, change-item reconstruction, footprint, delivery complexity, file surfaces
- `v0.2.0` - **semantic release intelligence**: evidence graph, release character, themes, risk/assurance/process findings, conservative rework signals, executive narrative, self-contained HTML
- `v0.3.0` - **delivery enrichment and history**: GitHub PR/review/CI/deployment evidence, consecutive-release baselines, relative metrics, hotspot and trend analysis
- `v0.4.0` - **agent interface**: MCP tools for snapshot, compare, explain, investigate, assess risk, trace a feature, and generate audience-specific briefs
- `v0.5.0` - **fleet ingestion**: optional clone/fetch adapters and multi-repository operation across GitHub and private/bare-metal Git while keeping local Git first-class

Claude Code, Copilot, ChatGPT, or another agent should be consumers of the evidence service rather than hard-coded dependencies of the product.

The target repositories should not need to vendor this code. They are inputs, not hosts.
