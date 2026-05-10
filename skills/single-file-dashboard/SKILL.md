---
name: single-file-dashboard
description: Build single-file zero-dependency interactive HTML dashboards for analytical artifacts that must be emailable, offline-viewable, or airgap-safe. Inline vanilla-SVG charts, no CDN, no remote scripts, no web fonts, no images. Useful for client deliverables, security audit reports, executive dashboards, post-mortems, technology consolidation analyses, and anything that needs to render identically in a browser, an email client, an airgapped laptop, or a regulator review. Use when the user asks for a "dashboard", "interactive HTML report", "shareable analysis", "offline dashboard", "airgap-safe report", or wants to turn an analytical workbook / dataset into a presentable HTML view.
---

# Single-File Dashboard

How to ship analytical artifacts as **single-file, fully self-contained, zero-dependency HTML dashboards** that render identically online, offline, on an airgapped laptop, and inside an email client.

**Companion rules:**

- `800-markdown.mdc` - markdown formatting for prose deliverables
- `810-documentation.mdc` - documentation patterns
- `815-reactflow-diagrams.mdc` - interactive React Flow canvases (the *other* dashboard pattern; see contrast below)

---

## When to invoke

Use when the user asks for:

- "Build a dashboard" / "interactive HTML report" / "shareable analysis"
- "Offline dashboard" / "airgap-safe" / "for the client" / "for the regulator"
- "Visualize this workbook" / "turn this CSV into a presentable view"
- An executive-style deliverable for client / leadership / regulator review
- Anything that must render without internet access

Do *not* use for:

- React applications (use a real frontend stack)
- Embedded analytics inside a webapp (use a charting library and your build pipeline)
- Real-time / streaming dashboards (use Grafana / Datadog / Looker)
- Interactive **architecture canvases** with custom nodes / edges - use `815-reactflow-diagrams.mdc` and the React Flow skill instead

---

## The Six Golden Rules

1. **One file. Zero dependencies.** No CDN, no remote scripts, no web fonts, no images. Inlined CSS, inlined JS, inlined data, inlined SVG.
2. **Inline vanilla SVG for charts.** No D3, Chart.js, ECharts, or React. Vanilla SVG renders everywhere; libraries do not.
3. **Escape user content.** Every string pulled from data must be HTML-escaped. Never bypass.
4. **Renders identically offline.** Test by disabling network; the dashboard must look unchanged.
5. **Renders identically in email.** Open the file in Gmail / Outlook / Apple Mail (as an attachment); layout must hold.
6. **Re-runnable, not editable.** Never edit generated HTML. Edit the generator and re-run.

---

## When to choose this pattern vs alternatives

| Need | Use this skill | Use React Flow | Use real BI tool | Use Markdown |
|---|---|---|---|---|
| Client / executive deliverable; must be emailable | yes | no | no | maybe |
| Airgap / regulated environment | yes | possibly (still SPA) | no | yes |
| Interactive architecture canvas with custom nodes | no | yes | no | no |
| Real-time / streaming data | no | no | yes | no |
| Analytical workbook -> shareable HTML | yes | no | maybe | no |
| Live KPIs across many sources | no | no | yes | no |
| Static narrative document | no | no | no | yes |

---

## Architecture

```
+--------------------------+
| Source artifact          |
| (xlsx / csv / json /     |
|  parquet / api dump)     |
+----------+---------------+
           |
           v
+--------------------------+
| Build script (Python)    |
|  - parse source          |
|  - shape model           |
|  - render HTML shell     |
|  - inline CSS, JS, SVG   |
|  - inline data as JSON   |
|    in <script> tags      |
+----------+---------------+
           |
           v
+--------------------------+
| Single-file HTML output  |
|  - no external requests  |
|  - opens with file://    |
+--------------------------+
```

The build script is the source of truth. The HTML is the artifact.

---

## Workflow

1. **Locate the source.** Excel workbook, CSV, JSON dump, parquet - whatever the upstream produced. If multiple candidates exist, ask the user.
2. **Define the dashboard sections.** Typical executive layout:
   - Overview (KPIs + thesis sentence)
   - Key decisions / findings
   - Charts (1-3 per section, never more)
   - Detail tables (sortable / filterable)
   - Risks / next steps
   - Methodology / source links
3. **Run the generator.**

   ```bash
   python3 build_dashboard.py --source <input>.xlsx --output <output>.html
   ```

4. **Verify offline.** Disable network; reload in browser. Anything that breaks (missing font, blank chart) violates the zero-dep guarantee.
5. **Verify in email client.** Save and reopen as an attachment in Gmail / Outlook. Layout must hold.
6. **Report back.** Summarize counts (sections rendered, items per section, charts), the absolute output path, and a `open <path>` command for macOS.

---

## Design system (executive palette)

A consistent design system makes outputs presentable without manual adjustment.

### Palette

| Token | Hex | Use |
|---|---|---|
| navy | `#051C2C` | Headlines, top rule, hero |
| slate | `#54758C` | Secondary text, axis labels |
| line | `#E1E6EB` | Borders, gridlines |
| accent blue | `#2251FF` | Primary action, links, key bars |
| positive green | `#0F6E3E` | Positive deltas, "what worked" callouts, retain decisions |
| negative red | `#B33A3A` | Negative deltas, "horror story" callouts, decommission decisions |
| warning amber | `#C18100` | Cautionary emphasis, contested decisions |
| neutral grey | `#6B7280` | Disabled / N/A states |

### Typography

- **System sans only** (Inter / SF / Segoe UI / Helvetica). No web fonts.
- Display 44px / Headline 28px / Subhead 20px / Body 15px / Caption 12px.
- All-caps 11px eyebrows with wide letter-spacing for section labels.
- Tabular nums for all numeric tables.

### Layout

- 1320px container, 56px gutters, 72px band padding.
- Top sticky nav (anchor links to sections).
- Horizontal-rule section dividers (no boxed cards everywhere).
- Tables: navy top rule, sticky headers, hover row highlight, no vertical gridlines.

### Chips & callouts

Standard chip styles for repeated semantics (decisions, severities, deltas, advantages):

```html
<span class="chip chip--retain">RETAIN</span>
<span class="chip chip--phase-out">PHASE OUT</span>
<span class="chip chip--severity-high">HIGH</span>
<span class="chip chip--shift-up">+0.42 vs balanced</span>
```

Green / amber / red callouts for evidence pairs (e.g., what-worked / horror-story from the multi-perspective-review skill).

---

## Charts (vanilla SVG)

The discipline that distinguishes this skill from "throw in a Chart.js script tag". Implement a small set of charts in pure SVG so the output never reaches for the network.

### Chart inventory (cover 90% of executive dashboards)

| Chart | Use |
|---|---|
| Horizontal bar | Decision mix, score comparison, ranked items |
| Vertical bar | Period comparison, category counts |
| Multi-series line | KPIs over time, success metrics |
| Gantt | Roadmap, phase plan |
| Stacked bar | Composition over time, mix shifts |
| Donut / pie | Avoid in executive dashboards; use horizontal bar instead |

### Skeleton

```javascript
// Vanilla SVG bar chart helper - inline in the dashboard, no imports.
function svgEl(name, attrs) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', name);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

function renderHbar(containerId, data, opts = {}) {
  const c = document.getElementById(containerId);
  const w = c.clientWidth, barH = opts.barH ?? 24, pad = 12;
  const max = Math.max(...data.map(d => d.value));
  const labelW = opts.labelW ?? 200;
  const svg = svgEl('svg', { width: w, height: data.length * (barH + pad) + pad });
  data.forEach((d, i) => {
    const y = pad + i * (barH + pad);
    svg.appendChild(svgEl('text', {
      x: 0, y: y + barH * 0.7, fill: 'var(--slate)',
      'font-size': '13', 'font-family': 'inherit',
    })).textContent = d.label;
    const barW = ((w - labelW - 60) * d.value) / max;
    svg.appendChild(svgEl('rect', {
      x: labelW, y, width: barW, height: barH,
      fill: opts.fill ?? 'var(--accent-blue)',
    }));
    svg.appendChild(svgEl('text', {
      x: labelW + barW + 6, y: y + barH * 0.7, fill: 'var(--navy)',
      'font-size': '13', 'font-family': 'inherit',
      'font-variant-numeric': 'tabular-nums',
    })).textContent = d.value.toLocaleString();
  });
  c.appendChild(svg);
}

window.addEventListener('resize', () => {
  document.querySelectorAll('[data-chart]').forEach(el => {
    el.innerHTML = '';
    renderChart(el.id);  // user-supplied dispatcher
  });
});
```

### Embedding the data

Inline as JSON in `<script type="application/json">` tags. Parse on init.

```html
<script type="application/json" id="decisionMixData">
  [
    {"label": "Retain", "value": 7},
    {"label": "Retain (Scoped)", "value": 3},
    {"label": "Phase out", "value": 2},
    {"label": "Decommission", "value": 1}
  ]
</script>

<div id="decisionMixChart" data-chart="hbar"></div>

<script>
  const data = JSON.parse(document.getElementById('decisionMixData').textContent);
  renderHbar('decisionMixChart', data);
</script>
```

The chart renders from JSON in the same file. No fetch. No network.

---

## Tooltips and interactions

Keep interactivity minimal and offline-friendly:

- **Hover tooltip** - one shared dark tooltip (custom div positioned at cursor); no library.
- **Click filters** - filter chips that show/hide rows in tables; pure CSS classes toggled with one event handler.
- **Sortable tables** - small `<th>` click handler that re-renders rows from the inlined JSON.
- **Section nav** - anchor links with smooth-scroll behavior via CSS.
- **No router** - URL fragments only.

Do not implement: drag-and-drop, infinite scroll, persistence (localStorage is fine; no backend).

---

## Build script structure (Python)

```python
# build_dashboard.py
from pathlib import Path
import argparse
import html
import json

PALETTE = {
    "navy": "#051C2C", "slate": "#54758C", "line": "#E1E6EB",
    "accent_blue": "#2251FF", "positive": "#0F6E3E",
    "negative": "#B33A3A", "warning": "#C18100", "neutral": "#6B7280",
}

HTML_SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>__TITLE__</title>
<style>
:root {
  --navy: __NAVY__;
  --slate: __SLATE__;
  /* ... */
}
body { margin: 0; font-family: Inter, system-ui, sans-serif; color: var(--navy); }
/* ... full CSS inlined here ... */
</style>
</head>
<body>
<nav class="topnav">__NAV__</nav>
<main>
  __OVERVIEW__
  __DECISIONS__
  __CHARTS__
  __DETAILS__
  __RATIONALE__
</main>
<script>
__JS__
</script>
</body>
</html>
"""

def render(source: Path, output: Path) -> None:
    data = parse_source(source)
    body = HTML_SHELL
    body = body.replace("__TITLE__", html.escape(data["title"]))
    for k, v in PALETTE.items():
        body = body.replace(f"__{k.upper()}__", v)
    body = body.replace("__OVERVIEW__", render_overview(data))
    body = body.replace("__DECISIONS__", render_decisions(data))
    body = body.replace("__CHARTS__", render_charts(data))
    body = body.replace("__JS__", JS_HELPERS)
    output.write_text(body, encoding="utf-8")

def render_overview(data):
    # All user content goes through html.escape()
    thesis = html.escape(data["thesis"])
    return f'<section><h1>{thesis}</h1></section>'

JS_HELPERS = """
function svgEl(name, attrs) { /* ... */ }
function renderHbar(id, data, opts) { /* ... */ }
"""

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    render(a.source, a.output or a.source.with_suffix(".html"))
```

The script writes a single string to disk. Test it by opening the output in a browser with the network disabled.

---

## Anti-patterns

1. **Linking to a CDN** for any asset. The dashboard breaks on airgap and in email; the guarantee is gone.
2. **Web fonts** (Google Fonts, Adobe Fonts). Falls back to system fonts in email anyway; just use system fonts.
3. **External images** (logos hosted on a CDN). Either inline as base64 SVG or omit.
4. **Charting library** (D3, Chart.js, ECharts, Plotly). Each adds 100-500KB and requires either a bundler or a CDN. Vanilla SVG is enough for executive charts.
5. **Generated HTML edited in place.** Make changes in the generator and re-run; otherwise the artifact and the source diverge.
6. **No HTML escaping.** A user-supplied product name with `<script>` in it becomes XSS in the dashboard.
7. **Donut / 3D / sunburst charts.** Hard to read at executive density. Use bar charts.
8. **More than 3 charts in a single section.** Cognitive load over signal.
9. **Localizing into the HTML** ("English en", "French fr") - use one language per output; multiple outputs for multiple languages.

---

## Testing checklist

- [ ] Open with network disabled; everything renders
- [ ] Open in Gmail / Outlook attachment view; layout holds
- [ ] Open in Safari / Chrome / Firefox / Edge; layout holds
- [ ] User-supplied strings with `<`, `>`, `&`, `"`, `'` render as text, not HTML
- [ ] Charts re-render correctly on window resize
- [ ] Sticky nav remains usable when scrolling
- [ ] Sortable tables sort correctly on every column
- [ ] Filter chips show/hide expected rows
- [ ] Print preview (Cmd-P) produces a usable PDF
- [ ] File size under 2 MB (data + chrome). If over, paginate or shrink the data.

---

## Distribution

- **Email** - attach. The recipient opens locally; no server.
- **Shared drive** - drop the HTML next to the source workbook.
- **Wiki / SharePoint** - upload as an attachment, not as a page (preserves the single-file guarantee).
- **GitHub Pages** - works, but the airgap-safe property is moot; consider a real SPA if you need GitHub Pages anyway.
- **Pinning a snapshot** - rename to `<analysis>-<YYYYMMDD>.html` so the artifact is self-dating.

---

## Related

- Rule: `800-markdown.mdc` - markdown formatting for non-HTML deliverables
- Rule: `810-documentation.mdc` - documentation patterns
- Rule: `815-reactflow-diagrams.mdc` - interactive React Flow canvases (different niche; SPA, not single-file)
- Skill: `multi-perspective-review` - panel review whose output renders cleanly into the Advisory section of this dashboard
- Skill: `documentation-standards` - companion patterns for narrative documentation

## Attribution

Pattern crystallized from an executive-style consolidation dashboard generator that produces single-file HTML output (no CDN, no fonts, no images, inline vanilla SVG) sized at <2 MB and renders identically in Chrome, Outlook, and on an airgapped laptop. The single-file/zero-dependency guarantee is the feature.
