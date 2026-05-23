"""StorePredict visual theme — design tokens, typography, and Quasar palette.

A single source of truth for the app's look. ``apply_theme()`` is called once per
page from :func:`store_predict.ui.layout.layout`; it injects the shared stylesheet
(once per process) and sets the Quasar brand palette for the page.

Direction — "Midnight Executive", matching the sibling tool vAtlas so the two
RVTools/VMware apps share one visual identity: a navy primary with a gold signal
accent over cool-slate surfaces, light + dark tokens, a navy command-bar header,
and tabular-figure numerics for capacity/DRR data.

Typography mirrors vAtlas: the system-ui stack for UI text (fast, native, no CDN)
and self-hosted JetBrains Mono for data/numbers (offline-friendly, served from
``/public/fonts`` by main.py).
"""

from __future__ import annotations

from nicegui import ui

# --- Quasar brand palette (drives buttons, switches, links, etc.) -----------
# vAtlas "Midnight Executive" hexes (OKLCH equivalents from its echarts theme).
PRIMARY = "#3245B7"  # navy-blue, interactive (primary-500)
SECONDARY = "#1E2761"  # deep navy (brand)
ACCENT = "#F9B935"  # gold signal accent
POSITIVE = "#4AA342"  # util-low green
NEGATIVE = "#DF202E"  # util-high red
WARNING = "#EF8700"  # util-mid orange
INFO = "#3245B7"

_BODY_STACK = "system-ui,-apple-system,'Segoe UI',Roboto,sans-serif"
_MONO_STACK = "'JetBrains Mono','Fira Code',ui-monospace,'SFMono-Regular',monospace"

_FONT_FACES = "".join(
    f"@font-face{{font-family:'JetBrains Mono';font-style:normal;font-weight:{weight};"
    f"font-display:swap;src:url('/public/fonts/JetBrainsMono-{weight}.woff2') format('woff2');}}"
    for weight in (400, 500)
)

_STYLESHEET = f"""
<style>
{_FONT_FACES}

:root {{
  --sp-canvas:#F8FAFC; --sp-surface:#FFFFFF; --sp-surface-2:#F1F5F9;
  --sp-ink:#0F172A; --sp-muted:#64748B; --sp-line:#E2E8F0;
  --sp-navy:#1E2761; --sp-primary:{PRIMARY}; --sp-primary-soft:#EAEEFB; --sp-ice:#B0C2F9;
  --sp-accent:{ACCENT};
  --sp-header:#1E2761;
  --sp-radius:8px; --sp-radius-sm:6px;
  --sp-shadow:0 1px 2px rgba(15,23,42,.06), 0 10px 28px -14px rgba(15,23,42,.22);
  --sp-font-body:{_BODY_STACK};
  --sp-font-display:{_BODY_STACK};
  --sp-font-mono:{_MONO_STACK};
}}
body.body--dark {{
  --sp-canvas:#0C0F16; --sp-surface:#161B24; --sp-surface-2:#11161F;
  --sp-ink:#F1F5F9; --sp-muted:#94A3B8; --sp-line:#232933;
  --sp-primary:#819AE9; --sp-primary-soft:#1A2440;
  --sp-header:#14182E;
  --sp-shadow:0 1px 2px rgba(0,0,0,.45), 0 12px 32px -16px rgba(0,0,0,.65);
}}

body, .q-page, .nicegui-content {{
  font-family:var(--sp-font-body);
  background:var(--sp-canvas); color:var(--sp-ink);
  -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
}}
h1,h2,h3,h4,.sp-display {{ font-weight:700; letter-spacing:-.02em; }}

/* Tabular figures for tabular/numeric data (capacity, DRR, counts). */
.q-table tbody td, .sp-num {{ font-variant-numeric:tabular-nums; font-feature-settings:'tnum' 1; }}
.sp-mono {{ font-family:var(--sp-font-mono); font-variant-numeric:tabular-nums; }}

/* Navy command-bar header with a thin gold rule. */
.sp-header {{
  background:var(--sp-header) !important; color:#E8EDFB;
  border-top:2px solid var(--sp-accent); box-shadow:var(--sp-shadow);
}}
.sp-brand {{
  font-weight:700; font-size:1.35rem; letter-spacing:-.022em;
  color:#FFFFFF; line-height:1;
}}
.sp-brand .sp-accent {{ color:var(--sp-accent); }}
.sp-nav-link {{
  color:var(--sp-ice); text-decoration:none; font-weight:500; font-size:.92rem;
  padding:.3rem .15rem; border-bottom:2px solid transparent;
  transition:color .15s ease, border-color .15s ease;
}}
.sp-nav-link:hover {{ color:#FFFFFF; border-bottom-color:var(--sp-accent); }}

/* Surfaces & accessibility polish. */
.sp-card {{
  background:var(--sp-surface); border:1px solid var(--sp-line);
  border-radius:var(--sp-radius); box-shadow:var(--sp-shadow);
}}
*:focus-visible {{ outline:2px solid var(--sp-accent); outline-offset:2px; border-radius:3px; }}
::selection {{ background:var(--sp-primary); color:#FFFFFF; }}
* {{ scrollbar-width:thin; scrollbar-color:var(--sp-line) transparent; }}

/* AG Grid (v34 themeQuartz + colorSchemeVariable): drive colors from our tokens.
   NiceGUI syncs data-ag-theme-mode with Quasar body--dark, so tokens swap too. */
.nicegui-aggrid {{
  --ag-font-family:var(--sp-font-body); --ag-font-size:13px;
  --ag-accent-color:var(--sp-primary);
  --ag-background-color:var(--sp-surface); --ag-foreground-color:var(--sp-ink);
  --ag-header-background-color:var(--sp-surface-2); --ag-header-text-color:var(--sp-muted);
  --ag-header-font-weight:600;
  --ag-border-color:var(--sp-line); --ag-row-border-color:var(--sp-line);
  --ag-row-hover-color:var(--sp-primary-soft);
  --ag-selected-row-background-color:var(--sp-primary-soft);
  --ag-control-panel-background-color:var(--sp-surface-2);
  --ag-input-focus-border-color:var(--sp-primary);
  --ag-wrapper-border-radius:var(--sp-radius);
}}

/* Confidence chips: green=deterministic override, navy=semantic, amber=Unknown/review. */
.sp-chip {{
  display:inline-flex; align-items:center; padding:1px 9px; border-radius:999px;
  font-size:11px; font-weight:600; letter-spacing:.01em; line-height:1.55;
  border:1px solid transparent;
}}
.sp-chip-override {{ background:#E7F4EC; color:#1F6B41; border-color:#BFE3CD; }}
.sp-chip-semantic {{ background:var(--sp-primary-soft); color:#2A357A; border-color:#C9D3F4; }}
.sp-chip-default  {{ background:#FCEEDD; color:#9A5A09; border-color:#F4D6B0; }}
.sp-chip-muted    {{ background:var(--sp-line); color:var(--sp-muted); }}
body.body--dark .sp-chip-override {{ background:#15301F; color:#79C99A; border-color:#1F4D30; }}
body.body--dark .sp-chip-semantic {{ background:#1A2440; color:#9BB0F0; border-color:#2A3A6B; }}
body.body--dark .sp-chip-default  {{ background:#3A2A12; color:#E0A75A; border-color:#5A4220; }}

/* Summary stat card: muted label, large tabular value, accent left edge. */
.sp-stat {{ border-left:3px solid var(--sp-accent); }}
.sp-stat-label {{
  font-size:.72rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase;
  color:var(--sp-muted);
}}
.sp-stat-value {{ font-size:1.7rem; font-weight:700; color:var(--sp-ink); font-variant-numeric:tabular-nums; }}
</style>
"""

_styles_registered = False


def apply_theme() -> None:
    """Apply the StorePredict theme to the current page.

    Injects the shared stylesheet once per process and sets the Quasar palette
    for this page. Safe to call from every page's layout entry point.
    """
    global _styles_registered
    if not _styles_registered:
        ui.add_head_html(_STYLESHEET, shared=True)
        _styles_registered = True
    ui.colors(
        primary=PRIMARY,
        secondary=SECONDARY,
        accent=ACCENT,
        positive=POSITIVE,
        negative=NEGATIVE,
        warning=WARNING,
        info=INFO,
    )
