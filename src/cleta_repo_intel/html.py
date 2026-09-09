from __future__ import annotations

from html import escape

from .models import EvidenceRef, ReleaseSnapshot


def _label(value: str) -> str:
    return value.replace("_", " ").title()


def _pill(text: str, css_class: str = "") -> str:
    class_attr = f"pill {css_class}".strip()
    return f'<span class="{class_attr}">{escape(text)}</span>'


def _evidence_links(evidence_by_id: dict[str, EvidenceRef], evidence_ids: list[str], limit: int = 6) -> str:
    rows = []
    for evidence_id in evidence_ids[:limit]:
        evidence = evidence_by_id.get(evidence_id)
        if not evidence:
            continue
        rows.append(f'<li><code>{escape(evidence.kind)}</code> {escape(evidence.label)}</li>')
    if len(evidence_ids) > limit:
        rows.append(f"<li>+{len(evidence_ids) - limit} more evidence record(s)</li>")
    return "<ul>" + "".join(rows) + "</ul>" if rows else "<p>No linked evidence.</p>"


def render_html(snapshot: ReleaseSnapshot) -> str:
    a = snapshot.activity
    c = snapshot.changes
    s = snapshot.signals
    intel = snapshot.intelligence
    evidence_by_id = {evidence.id: evidence for evidence in intel.evidence}
    max_work = max(snapshot.work_types.values(), default=1)
    work_bars = "".join(
        f'<div class="bar-row"><span>{escape(_label(kind))}</span><div class="bar"><i style="width:{max(5, int(count / max_work * 100))}%"></i></div><strong>{count}</strong></div>'
        for kind, count in sorted(snapshot.work_types.items(), key=lambda item: (-item[1], item[0]))
    )
    theme_cards = "".join(
        f'''<article class="card theme"><div class="card-head"><h3>{escape(theme.name)}</h3>{_pill(str(theme.change_items) + " change items")}</div>
        <details><summary>Evidence</summary>{_evidence_links(evidence_by_id, theme.evidence_ids)}</details></article>'''
        for theme in intel.themes
    ) or '<article class="card"><p>No dominant themes detected.</p></article>'
    finding_cards = "".join(
        f'''<article class="card finding {escape(finding.level)}"><div class="card-head"><h3>{escape(finding.title)}</h3>{_pill(finding.level.upper(), finding.level)}</div>
        <p>{escape(finding.summary)}</p><small>{escape(finding.kind.title())} finding - confidence {escape(finding.confidence)}</small>
        <details><summary>Evidence</summary>{_evidence_links(evidence_by_id, finding.evidence_ids)}</details></article>'''
        for finding in intel.findings
    ) or '<article class="card"><p>No elevated findings detected.</p></article>'
    rework = "".join(
        f'<li><strong>{signal.count}x</strong> {escape(signal.label)}</li>' for signal in intel.rework_signals
    ) or '<li>No repeated change-item signals detected.</li>'
    areas = "".join(f"<tr><td>{escape(area.name)}</td><td>{area.files}</td></tr>" for area in snapshot.areas)
    evidence_rows = "".join(
        f"<tr><td><code>{escape(e.id)}</code></td><td>{escape(e.kind)}</td><td>{escape(e.label)}</td><td>{escape(e.detail)}</td></tr>"
        for e in intel.evidence
    )
    warnings = "".join(f"<li>{escape(warning)}</li>" for warning in snapshot.warnings) or "<li>None.</li>"
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(snapshot.repository)} release intelligence</title>
<style>
:root {{ color-scheme: light dark; --bg:#0b1020; --panel:#141b2d; --text:#edf2ff; --muted:#aab4ca; --line:#2a3550; --accent:#7aa2ff; --good:#54d39a; --warn:#ffbe55; --risk:#ff7185; }}
* {{ box-sizing:border-box; }} body {{ margin:0; font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--bg); color:var(--text); line-height:1.5; }}
main {{ max-width:1180px; margin:auto; padding:32px 20px 72px; }} h1,h2,h3,p {{ margin-top:0; }} h1 {{ font-size:clamp(2rem,5vw,4rem); line-height:1; }} h2 {{ margin-top:36px; }}
.hero {{ padding:32px; border:1px solid var(--line); border-radius:24px; background:linear-gradient(135deg,#18213a,#0f1627); }} .eyebrow {{ color:var(--accent); text-transform:uppercase; letter-spacing:.12em; font-size:.8rem; font-weight:700; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; }} .metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-top:22px; }}
.metric,.card {{ border:1px solid var(--line); border-radius:16px; background:var(--panel); padding:18px; }} .metric strong {{ display:block; font-size:1.7rem; }} .metric span, small {{ color:var(--muted); }}
.pill {{ display:inline-block; border:1px solid var(--line); border-radius:999px; padding:4px 9px; font-size:.75rem; white-space:nowrap; }} .pill.high {{ border-color:var(--risk); color:var(--risk); }} .pill.medium {{ border-color:var(--warn); color:var(--warn); }} .pill.positive {{ border-color:var(--good); color:var(--good); }} .pill.info {{ border-color:var(--accent); color:var(--accent); }}
.card-head {{ display:flex; gap:12px; align-items:flex-start; justify-content:space-between; }} .finding.high {{ border-left:4px solid var(--risk); }} .finding.medium {{ border-left:4px solid var(--warn); }} .finding.positive {{ border-left:4px solid var(--good); }} .finding.info {{ border-left:4px solid var(--accent); }}
details {{ margin-top:12px; }} summary {{ cursor:pointer; color:var(--accent); }} code {{ color:#c6d5ff; }} table {{ width:100%; border-collapse:collapse; }} td,th {{ border-bottom:1px solid var(--line); text-align:left; padding:9px; vertical-align:top; }}
.bar-row {{ display:grid; grid-template-columns:110px 1fr 44px; gap:10px; align-items:center; margin:8px 0; }} .bar {{ height:10px; border-radius:999px; background:#202b45; overflow:hidden; }} .bar i {{ display:block; height:100%; background:var(--accent); border-radius:inherit; }}
.story {{ font-size:1.15rem; max-width:900px; }} .muted {{ color:var(--muted); }} .evidence-table {{ overflow:auto; }} ul {{ padding-left:20px; }}
@media (prefers-color-scheme:light) {{ :root {{ --bg:#f5f7fb; --panel:#fff; --text:#172033; --muted:#5b6780; --line:#dce2ed; --accent:#315fca; }} .hero {{ background:linear-gradient(135deg,#eef3ff,#fff); }} code {{ color:#315fca; }} .bar {{ background:#e5eaf3; }} }}
</style>
</head>
<body><main>
<section class="hero">
<div class="eyebrow">Cleta Release Intelligence - schema {escape(snapshot.schema_version)}</div>
<h1>{escape(snapshot.repository)}</h1>
<p class="story">{escape(intel.narrative)}</p>
<div>{_pill(_label(s.footprint) + " footprint")} {_pill(_label(s.delivery_complexity) + " complexity", "high" if s.delivery_complexity == "high" else "medium" if s.delivery_complexity == "medium" else "info")} {_pill(_label(intel.release_character))}</div>
<div class="metrics">
<div class="metric"><strong>{a.change_items}</strong><span>detected change items</span></div>
<div class="metric"><strong>{c.files_changed}</strong><span>files changed</span></div>
<div class="metric"><strong>{c.churn:,}</strong><span>lines of churn</span></div>
<div class="metric"><strong>{s.surfaces_touched}</strong><span>repository surfaces</span></div>
<div class="metric"><strong>{a.git_commits}</strong><span>visible Git commits</span></div>
<div class="metric"><strong>{len(intel.evidence)}</strong><span>evidence records</span></div>
</div>
</section>

<h2>What actually changed</h2><div class="grid">{theme_cards}</div>
<h2>What deserves attention</h2><div class="grid">{finding_cards}</div>
<h2>Iteration signals</h2><section class="card"><ul>{rework}</ul><p class="muted">Repeated change language is evidence of iteration, not a working-hours or productivity metric.</p></section>
<h2>Work composition</h2><section class="card">{work_bars}</section>
<h2>Major areas changed</h2><section class="card"><table><thead><tr><th>Area</th><th>Files</th></tr></thead><tbody>{areas}</tbody></table></section>
<h2>Evidence & provenance</h2><section class="card"><p><strong>Base:</strong> <code>{escape(snapshot.refs.base_ref)}</code> -> <code>{escape(snapshot.refs.base_sha)}</code><br><strong>Head:</strong> <code>{escape(snapshot.refs.head_ref)}</code> -> <code>{escape(snapshot.refs.head_sha)}</code></p><details><summary>Show all evidence</summary><div class="evidence-table"><table><thead><tr><th>ID</th><th>Kind</th><th>Label</th><th>Detail</th></tr></thead><tbody>{evidence_rows}</tbody></table></div></details></section>
<h2>Warnings</h2><section class="card"><ul>{warnings}</ul></section>
<p class="muted">Derived from repository evidence. Not an estimate of hours worked or individual productivity.</p>
</main></body></html>'''
