"""Export the executed notebook as a formatted, self-contained HTML report.

Usage, after the notebook has been run, in the ISR environment:

    python export_html.py      # from this folder; from anywhere else, give the script's path

The notebook itself is not changed and not re-run. nbconvert renders it without
the In/Out prompts, and this script lays a report design over the result:

- a title block (title, byline, generation date, opening paragraph) and a
  contents sidebar with the current section highlighted;
- code hidden by default, with a "Show code" button on every code block and a
  "Show all code" switch in the sidebar;
- one table style throughout: rules above and below each table and under its
  header, text left-aligned and numbers right-aligned, captioned tables numbered
  in order of appearance, wide tables scrolling instead of overflowing;
- figures on the page with their captions beneath, also used as alt text;
- the "Interpretation" and "Caveat" boxes styled as titled callouts.

Everything stays in one file, so the report opens offline in any browser.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import nbformat
from nbconvert import HTMLExporter

HERE = Path(__file__).resolve().parent
NOTEBOOK = HERE / "statistical_analysis.ipynb"
OUTPUT = HERE / "statistical_analysis.html"

CSS = r"""
:root {
  --r-ink: #1a1d21;
  --r-ink-2: #4a525c;
  --r-muted: #7b848e;
  --r-rule: #1a1d21;
  --r-line: #d5dae0;
  --r-hair: #e6e9ed;
  --r-accent: #2c4a6e;
  --r-accent-soft: #f4f6f9;
  --r-caveat: #8a5d14;
  --r-caveat-soft: #fbf7ef;
  --r-code-bg: #f6f8fa;
  --r-sidebar: 264px;
  --r-content: 900px;
  --r-serif: Charter, "Bitstream Charter", "Sitka Text", Cambria, "Iowan Old Style", Georgia, serif;
  --r-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  --r-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
  --jp-content-font-family: var(--r-serif);
  --jp-ui-font-family: var(--r-sans);
  --jp-code-font-family: var(--r-mono);
  --jp-content-font-color1: var(--r-ink);
  --jp-content-link-color: var(--r-accent);
  color-scheme: light;
}
html { scroll-behavior: smooth; scroll-padding-top: 20px; }
body.jp-Notebook {
  background: #fff; color: var(--r-ink); font-family: var(--r-serif);
  margin: 0; padding: 0 0 0 var(--r-sidebar); overflow: visible;
}
main { max-width: var(--r-content); margin: 0 auto; padding: 52px 48px 112px; box-sizing: border-box; }

/* ---------- cells ---------- */
.jp-Collapser, .jp-InputPrompt, .jp-OutputPrompt { display: none !important; }
.jp-Cell { padding: 0 !important; margin: 0 !important; }
.jp-Cell-inputWrapper, .jp-Cell-outputWrapper { margin: 0; }
.jp-Cell:not(.jp-mod-noOutputs) .jp-Cell-outputWrapper { margin-top: 0; }
.jp-MarkdownOutput, .jp-RenderedMarkdown { padding: 0 !important; }
.jp-OutputArea-output { padding: 0; overflow-x: auto; }
.jp-OutputArea-child { margin: 0; }

/* ---------- text ---------- */
.jp-RenderedHTMLCommon {
  font-family: var(--r-serif); font-size: 16px; line-height: 1.62; color: var(--r-ink); padding-right: 0;
}
.jp-RenderedHTMLCommon p { margin: 0 0 14px; }
.jp-RenderedHTMLCommon h1, .jp-RenderedHTMLCommon h2,
.jp-RenderedHTMLCommon h3, .jp-RenderedHTMLCommon h4 { font-family: var(--r-sans); color: var(--r-ink); }
/* Jupyter gives headings that open or close a cell their own margins; these rules restore one spacing. */
.jp-RenderedHTMLCommon h1, .jp-RenderedHTMLCommon h1:first-child, .jp-RenderedHTMLCommon h1:last-child {
  font-size: 30px; line-height: 1.2; font-weight: 700; letter-spacing: -0.01em; margin: 0 0 14px;
}
.jp-RenderedHTMLCommon h2, .jp-RenderedHTMLCommon h2:first-child, .jp-RenderedHTMLCommon h2:last-child {
  font-size: 22px; line-height: 1.3; font-weight: 650; margin: 60px 0 16px;
  padding-bottom: 8px; border-bottom: 1px solid var(--r-line);
}
.jp-RenderedHTMLCommon h3, .jp-RenderedHTMLCommon h3:first-child, .jp-RenderedHTMLCommon h3:last-child {
  font-size: 17.5px; line-height: 1.35; font-weight: 650; margin: 36px 0 12px;
}
.jp-RenderedHTMLCommon h4, .jp-RenderedHTMLCommon h4:first-child, .jp-RenderedHTMLCommon h4:last-child {
  font-size: 15px; line-height: 1.4; font-weight: 650; margin: 28px 0 10px;
}
.jp-RenderedHTMLCommon code {
  font-family: var(--r-mono); font-size: 0.84em; background: #f1f3f5;
  padding: 0.1em 0.35em; border-radius: 3px; color: #24292f;
}
.jp-RenderedHTMLCommon a { color: var(--r-accent); text-decoration: none; }
.jp-RenderedHTMLCommon a:hover { text-decoration: underline; }
.jp-RenderedHTMLCommon a.anchor-link { opacity: 0; margin-left: 6px; color: var(--r-muted); font-weight: 400; }
.jp-RenderedHTMLCommon h2:hover a.anchor-link, .jp-RenderedHTMLCommon h3:hover a.anchor-link,
.jp-RenderedHTMLCommon h4:hover a.anchor-link { opacity: 1; text-decoration: none; }
.jp-RenderedHTMLCommon ul, .jp-RenderedHTMLCommon ol { padding-left: 22px; margin: 0 0 14px; }
.jp-RenderedHTMLCommon li { margin: 4px 0; }

/* title block */
.jp-Cell.report-title { padding-bottom: 24px !important; border-bottom: 1px solid var(--r-line); }
.report-title p.byline { font-family: var(--r-sans); font-size: 14.5px; color: var(--r-ink-2); margin: 0 0 3px; }
.report-title p.report-meta { font-family: var(--r-sans); font-size: 13px; color: var(--r-muted); margin: 0 0 22px; }
.report-title p.lead { font-size: 17.5px; line-height: 1.6; margin: 0; }
.report-title + .jp-Cell .jp-RenderedMarkdown > h2:first-child { margin-top: 40px; }

/* callouts: "Interpretation", "Caveat" */
.jp-RenderedHTMLCommon blockquote {
  margin: 18px 0 28px; padding: 14px 20px; background: var(--r-accent-soft);
  border: none; border-left: 3px solid var(--r-accent); border-radius: 0; color: var(--r-ink); font-size: 15.5px;
}
.jp-RenderedHTMLCommon blockquote > :last-child { margin-bottom: 0; }
.jp-RenderedHTMLCommon blockquote p.callout-title {
  font-family: var(--r-sans); font-size: 14px; font-weight: 650; color: var(--r-accent); margin: 0 0 6px;
}
.jp-RenderedHTMLCommon blockquote ul { margin: 0 0 10px; padding-left: 20px; }
.jp-RenderedHTMLCommon blockquote li { margin: 6px 0; }
.jp-RenderedHTMLCommon blockquote.callout-caveat { background: var(--r-caveat-soft); border-left-color: var(--r-caveat); }
.jp-RenderedHTMLCommon blockquote.callout-caveat p.callout-title { color: var(--r-caveat); }

/* ---------- tables: one style for every table ---------- */
.table-wrap { overflow-x: auto; margin: 10px 0 28px; }
/* Jupyter's last-child rule (margin-bottom: 0.5em) would cut these gaps to 8 px at the end of a cell */
.jp-RenderedHTMLCommon > .table-wrap:last-child { margin-bottom: 28px; }
.jp-RenderedHTMLCommon > p.fig-caption:last-child { margin-bottom: 26px; }
.jp-RenderedHTMLCommon > blockquote:last-child { margin-bottom: 28px; }
.jp-RenderedHTMLCommon table {
  width: 100% !important; max-width: none; table-layout: auto !important;
  border-collapse: collapse !important; border-spacing: 0; margin: 0 !important;
  border: none !important; border-top: 1.5px solid var(--r-rule) !important;
  border-bottom: 1.5px solid var(--r-rule) !important; border-radius: 0 !important;
  background: transparent !important; color: var(--r-ink);
  font-family: var(--r-sans) !important; font-size: 13px !important; line-height: 1.45 !important;
  font-variant-numeric: tabular-nums lining-nums;
}
.jp-RenderedHTMLCommon th, .jp-RenderedHTMLCommon td {
  padding: 6px 9px !important; border: none !important; border-bottom: 1px solid var(--r-hair) !important;
  vertical-align: top !important; background: transparent !important; line-height: 1.45 !important;
  white-space: normal; max-width: none;
}
/* Text left, numbers right: Jupyter right-aligns every output cell, and the per-column rules from the
   notebook (pandas Styler, ID selectors) still win over this one. */
.jp-RenderedMarkdown.jp-RenderedHTMLCommon th, .jp-RenderedMarkdown.jp-RenderedHTMLCommon td,
.jp-OutputArea-output.jp-RenderedHTMLCommon th, .jp-OutputArea-output.jp-RenderedHTMLCommon td { text-align: left; }
.jp-RenderedHTMLCommon thead th {
  font-weight: 600 !important; vertical-align: bottom !important; border-bottom: 1px solid var(--r-rule) !important;
}
/* Two-level headers: the upper row names a group of columns, with a short rule beneath */
.jp-RenderedHTMLCommon thead tr:not(:last-child) th { border-bottom: none !important; padding-bottom: 2px !important; }
.jp-RenderedHTMLCommon thead tr:not(:last-child) th.span-head {
  text-align: center !important; white-space: nowrap !important; border-bottom: 1px solid var(--r-line) !important;
}
.jp-RenderedHTMLCommon tbody tr:last-child td, .jp-RenderedHTMLCommon tbody tr:last-child th { border-bottom: none !important; }
.jp-RenderedHTMLCommon tbody tr, .jp-RenderedHTMLCommon tbody tr:nth-child(odd),
.jp-RenderedHTMLCommon tbody tr:nth-child(even), .jp-RenderedHTMLCommon tbody tr:hover { background: transparent !important; }
.jp-RenderedHTMLCommon caption {
  caption-side: top !important; text-align: left !important; padding: 0 0 8px !important;
  font-family: var(--r-sans) !important; font-size: 13.5px !important; font-weight: 400 !important;
  line-height: 1.5 !important; color: var(--r-ink-2) !important;
}
.jp-RenderedHTMLCommon caption .tbl-label { font-weight: 700; color: var(--r-ink); }
.jp-RenderedHTMLCommon td code { font-size: 0.92em; }
td.nowrap, th.nowrap { white-space: nowrap !important; }
.nobr { white-space: nowrap; }
.verdict-tag {
  display: block; font-size: 11px; color: var(--r-ink-2); margin-top: 1px;
  white-space: nowrap; font-weight: 400; font-style: normal;
}

/* ---------- figures ---------- */
.jp-RenderedImage { background: none !important; border: none; padding: 0; margin: 22px 0 8px; box-shadow: none; }
.jp-RenderedImage img { display: block; max-width: 100%; height: auto; margin: 0 auto; }
p.fig-caption { font-family: var(--r-sans); font-size: 13.5px; line-height: 1.5; color: var(--r-ink-2); margin: 6px 0 26px; }
p.fig-caption strong:first-child { color: var(--r-ink); }

/* ---------- code ---------- */
.jp-CodeCell .jp-Cell-inputWrapper { display: none; }
.jp-CodeCell.code-open .jp-Cell-inputWrapper { display: block; }
.code-toggle {
  display: inline-flex; align-items: center; gap: 7px; margin: 2px 0 8px; padding: 3px 0;
  font-family: var(--r-sans); font-size: 12.5px; font-weight: 500; line-height: 1.4;
  color: var(--r-muted); background: none; border: none; cursor: pointer;
}
.code-toggle::before {
  content: ""; border-left: 5px solid currentColor; border-top: 4px solid transparent;
  border-bottom: 4px solid transparent; transition: transform 0.15s ease;
}
.jp-CodeCell.code-open > .code-toggle::before { transform: rotate(90deg); }
.code-toggle:hover { color: var(--r-ink); }
.code-toggle:focus-visible { outline: 2px solid var(--r-accent); outline-offset: 2px; border-radius: 2px; }
.jp-InputArea-editor {
  background: var(--r-code-bg) !important; border: 1px solid var(--r-hair) !important; border-radius: 4px;
  padding: 10px 14px !important; margin: 0 0 12px; overflow-x: auto;
}
.jp-InputArea-editor pre, .jp-InputArea-editor .highlight pre {
  font-family: var(--r-mono) !important; font-size: 12.5px !important; line-height: 1.5 !important;
}
.jp-RenderedMarkdown .highlight, .jp-InputArea-editor .highlight { background: none; }
.jp-RenderedMarkdown pre {
  background: var(--r-code-bg); border: 1px solid var(--r-hair) !important; border-radius: 4px;
  padding: 10px 14px !important; margin: 4px 0 16px !important; overflow-x: auto;
  font-family: var(--r-mono); font-size: 12.5px !important; line-height: 1.5;
}
.jp-RenderedMarkdown pre code { background: none; padding: 0; font-size: 1em; }
.jp-RenderedText pre {
  font-family: var(--r-mono); font-size: 12.5px !important; line-height: 1.5; color: var(--r-ink-2);
  background: none; border-left: 2px solid var(--r-line) !important; padding: 2px 0 2px 12px !important;
  margin: 4px 0 16px !important; white-space: pre-wrap;
}

/* ---------- sidebar ---------- */
#report-nav {
  position: fixed; top: 0; left: 0; bottom: 0; width: var(--r-sidebar); box-sizing: border-box;
  overflow-y: auto; background: #fbfbfc; border-right: 1px solid var(--r-hair);
  padding: 30px 16px 28px 22px; font-family: var(--r-sans); font-size: 13px; z-index: 10;
}
#report-nav .nav-title { font-size: 14px; font-weight: 700; line-height: 1.35; color: var(--r-ink); }
#report-nav .nav-sub { font-size: 12.5px; color: var(--r-muted); margin: 4px 0 16px; }
#report-nav .nav-controls { margin-bottom: 22px; }
#report-nav button {
  font-family: var(--r-sans); font-size: 12px; font-weight: 600; color: var(--r-ink-2); background: #fff;
  border: 1px solid var(--r-line); border-radius: 4px; padding: 5px 11px; cursor: pointer;
}
#report-nav button:hover { border-color: var(--r-ink-2); color: var(--r-ink); }
#report-nav button:focus-visible { outline: 2px solid var(--r-accent); outline-offset: 2px; }
#report-nav .nav-heading { font-size: 12.5px; font-weight: 700; color: var(--r-ink); margin: 0 0 6px 10px; }
#report-nav ol { list-style: none; margin: 0; padding: 0; }
#report-nav li { margin: 0; }
#report-nav a {
  display: block; padding: 4px 8px 4px 10px; margin: 1px 0; color: var(--r-ink-2); text-decoration: none;
  border-left: 2px solid transparent; line-height: 1.35;
}
#report-nav a:hover { color: var(--r-ink); }
#report-nav a.active { color: var(--r-ink); font-weight: 600; border-left-color: var(--r-accent); }
#report-nav li.sub a { padding-left: 22px; font-size: 12.5px; }

@media (max-width: 1100px) {
  body.jp-Notebook { padding-left: 0; }
  #report-nav { position: static; width: auto; border-right: none; border-bottom: 1px solid var(--r-hair); }
  #report-nav .nav-title, #report-nav .nav-sub { display: none; }
  #report-nav ol { columns: 2; column-gap: 28px; }
  #report-nav li { break-inside: avoid; }
  main { padding: 28px 18px 64px; }
}

@media print {
  #report-nav, .code-toggle { display: none !important; }
  body.jp-Notebook { padding: 0; }
  main { max-width: none; padding: 0; }
  .jp-RenderedImage, table, blockquote, p.fig-caption { break-inside: avoid; }
  .jp-RenderedHTMLCommon h2, .jp-RenderedHTMLCommon h3, .jp-RenderedHTMLCommon h4 { break-after: avoid; }
  a.anchor-link { display: none; }
}
"""

NAV = """
<nav id="report-nav" aria-label="Contents">
  <div class="nav-title">Rapamycin after stroke in aged rats</div>
  <div class="nav-sub">Statistical analysis · Assignment S1</div>
  <div class="nav-controls">
    <button id="toggle-code" type="button">Show all code</button>
  </div>
  <div class="nav-heading">Contents</div>
  <ol id="nav-list"></ol>
</nav>
"""

JS = r"""
<script>
(function () {
  // Title block: title, byline, generation date and opening paragraph
  const first = document.querySelector("main .jp-MarkdownCell");
  if (first) {
    first.classList.add("report-title");
    const paras = first.querySelectorAll(".jp-RenderedMarkdown > p");
    if (paras[0]) {
      paras[0].classList.add("byline");
      const meta = document.createElement("p");
      meta.className = "report-meta";
      meta.textContent = "__GENERATED__";
      paras[0].after(meta);
    }
    if (paras[1]) paras[1].classList.add("lead");
  }

  // A "Show code" button on every code block, and one switch for all of them
  const allToggle = document.getElementById("toggle-code");
  const codeCells = Array.from(document.querySelectorAll("main .jp-CodeCell")).filter(function (cell) {
    return cell.querySelector(":scope > .jp-Cell-inputWrapper");
  });
  function setOpen(cell, open) {
    cell.classList.toggle("code-open", open);
    const button = cell.querySelector(":scope > .code-toggle");
    button.textContent = open ? "Hide code" : "Show code";
    button.setAttribute("aria-expanded", String(open));
  }
  function syncAllToggle() {
    const allOpen = codeCells.every(function (cell) { return cell.classList.contains("code-open"); });
    allToggle.textContent = allOpen ? "Hide all code" : "Show all code";
    allToggle.dataset.open = String(allOpen);
  }
  codeCells.forEach(function (cell, i) {
    const input = cell.querySelector(":scope > .jp-Cell-inputWrapper");
    input.id = "code-block-" + (i + 1);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "code-toggle";
    button.setAttribute("aria-controls", input.id);
    cell.insertBefore(button, input);
    setOpen(cell, false);
    button.addEventListener("click", function () {
      setOpen(cell, !cell.classList.contains("code-open"));
      syncAllToggle();
    });
  });
  allToggle.addEventListener("click", function () {
    const open = allToggle.dataset.open !== "true";
    codeCells.forEach(function (cell) { setOpen(cell, open); });
    syncAllToggle();
  });
  syncAllToggle();

  // "§ 4", "21 %", "10 pp", "8.8 mm³" and "n = 64" never break across lines. A no-wrap span keeps the
  // ordinary space; a non-breaking space would show as a double gap in Charter.
  const NO_BREAK = /(§ \d|\d (?:%|pp\b|mm³|h\b|min\b|SD\b)|n = \d+|probe \d)/;
  const walker = document.createTreeWalker(document.querySelector("main"), NodeFilter.SHOW_TEXT, {
    acceptNode: function (node) {
      return node.parentElement.closest("pre, code, script, style") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
    }
  });
  const found = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (NO_BREAK.test(node.nodeValue)) found.push(node);
  }
  found.forEach(function (node) {
    node.replaceWith.apply(node, node.nodeValue.split(NO_BREAK).map(function (part, i) {
      if (i % 2 === 0) return part;
      const span = document.createElement("span");
      span.className = "nobr";
      span.textContent = part;
      return span;
    }));
  });

  // Callouts: a blockquote that opens with a bold-only line takes it as its title
  document.querySelectorAll("main .jp-RenderedMarkdown blockquote").forEach(function (quote) {
    const head = quote.firstElementChild;
    if (head && head.tagName === "P" && head.children.length === 1 && head.firstElementChild.tagName === "STRONG"
        && head.textContent.trim() === head.firstElementChild.textContent.trim()) {
      head.classList.add("callout-title");
      if (/^caveat$/i.test(head.textContent.trim())) quote.classList.add("callout-caveat");
    }
  });

  // Data tables: the verdict is shown the same way everywhere, as a small label under
  // its adjusted p-value, and short numeric values never break across lines
  const VERDICTS = ["clear", "suggestive", "not significant"];
  function addTag(td, verdict) {
    const tag = document.createElement("span");
    tag.className = "verdict-tag";
    tag.textContent = verdict;
    td.appendChild(tag);
    td.classList.add("nowrap");
  }
  document.querySelectorAll('main .jp-OutputArea-output table[id^="T_"]').forEach(function (table) {
    table.querySelectorAll("td").forEach(function (td) {
      const m = td.textContent.trim().match(/^(.+?) · (clear|suggestive|not significant)$/);
      if (m) { td.textContent = m[1]; addTag(td, m[2]); }
    });
    const headRow = table.tHead ? table.tHead.rows[table.tHead.rows.length - 1] : null;
    if (headRow && table.tBodies[0]) {
      const names = Array.from(headRow.cells).map(function (th) { return th.textContent.trim(); });
      const v = names.indexOf("Verdict");
      let p = -1;
      names.forEach(function (name, i) { if (/^p( |$)/.test(name)) p = i; });
      const rows = Array.from(table.tBodies[0].rows);
      if (v >= 0 && p >= 0 && rows.every(function (row) { return VERDICTS.includes(row.cells[v].textContent.trim()); })) {
        rows.forEach(function (row) { addTag(row.cells[p], row.cells[v].textContent.trim()); row.cells[v].remove(); });
        headRow.cells[v].remove();
      }
    }
    table.querySelectorAll("td").forEach(function (td) {
      const text = td.textContent.trim();
      if (text.length <= 22 && /\d/.test(text)) td.classList.add("nowrap");
    });
    table.querySelectorAll("thead th").forEach(function (th) {
      if (th.textContent.trim().length <= 9) th.classList.add("nowrap");
    });
    if (table.tHead) {
      Array.from(table.tHead.rows).slice(0, -1).forEach(function (row) {
        Array.from(row.cells).forEach(function (th) { if (th.textContent.trim()) th.classList.add("span-head"); });
      });
    }
  });

  // Every table: empty header rows dropped, a scrolling wrapper, numbered captions,
  // and headers aligned like the cells of their column
  let tableNumber = 0;
  document.querySelectorAll("main table").forEach(function (table) {
    if (table.tHead && Array.from(table.tHead.querySelectorAll("th")).every(function (th) {
      return th.textContent.trim() === "";
    })) table.tHead.remove();

    if (table.tBodies[0]) Array.from(table.tBodies[0].rows).forEach(function (row) {
      if (row.cells[0] && row.cells[0].textContent.trim().length <= 20) row.cells[0].classList.add("nowrap");
    });

    const wrap = document.createElement("div");
    wrap.className = "table-wrap";
    table.parentNode.insertBefore(wrap, table);
    wrap.appendChild(table);

    const caption = table.querySelector("caption");
    if (caption && caption.textContent.trim()) {
      tableNumber += 1;
      const label = document.createElement("span");
      label.className = "tbl-label";
      label.textContent = "Table " + tableNumber + ". ";
      caption.insertBefore(label, caption.firstChild);
    }

    const body = table.tBodies[0];
    const headRow = table.tHead ? table.tHead.rows[table.tHead.rows.length - 1] : null;
    if (body && headRow) {
      Array.from(headRow.cells).forEach(function (th, i) {
        const column = Array.from(body.rows).map(function (row) { return row.cells[i]; }).filter(Boolean);
        if (column.length && column.every(function (td) { return getComputedStyle(td).textAlign === "right"; })) {
          th.style.textAlign = "right";
        }
      });
    }
  });

  // Figure captions ("**Figure N.** ..."), also used as the images' alt text
  document.querySelectorAll("main .jp-RenderedMarkdown p").forEach(function (p) {
    const lead = p.firstElementChild;
    if (lead && lead.tagName === "STRONG" && /^Figure \d+/.test(lead.textContent) && p.firstChild === lead) {
      p.classList.add("fig-caption");
    }
  });
  const cells = Array.from(document.querySelectorAll("main .jp-Cell"));
  cells.forEach(function (cell, i) {
    const img = cell.querySelector(".jp-RenderedImage img");
    if (!img) return;
    for (let j = i + 1; j < Math.min(cells.length, i + 3); j++) {
      const cap = cells[j].querySelector("p.fig-caption");
      if (cap) { img.alt = cap.textContent.trim().slice(0, 400); break; }
    }
  });

  // Contents sidebar with the current section highlighted
  const list = document.getElementById("nav-list");
  const heads = Array.from(document.querySelectorAll("main .jp-MarkdownCell h2[id], main .jp-MarkdownCell h3[id]"));
  const links = new Map();
  heads.forEach(function (h) {
    const li = document.createElement("li");
    if (h.tagName === "H3") li.className = "sub";
    const a = document.createElement("a");
    a.href = "#" + h.id;
    a.textContent = h.textContent.replace(/¶\s*$/, "").trim();
    li.appendChild(a);
    list.appendChild(li);
    links.set(h, a);
  });
  const nav = document.getElementById("report-nav");
  let current = null;
  function update() {
    let active = heads[0];
    for (const h of heads) { if (h.getBoundingClientRect().top < 60) active = h; else break; }
    if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) active = heads[heads.length - 1];
    if (active !== current) {
      if (current) links.get(current).classList.remove("active");
      if (active) {
        const a = links.get(active);
        a.classList.add("active");
        // Only the fixed sidebar follows the reader; in narrow windows it sits above the report and must not move the page
        if (getComputedStyle(nav).position === "fixed") a.scrollIntoView({ block: "nearest" });
      }
      current = active;
    }
  }
  window.addEventListener("scroll", update, { passive: true });
  update();
})();
</script>
"""


def main() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    exporter = HTMLExporter(template_name="lab", exclude_input_prompt=True, exclude_output_prompt=True)
    html, _ = exporter.from_notebook_node(notebook)

    today = date.today()
    generated = f"Report generated {today.day} {today:%B %Y} from {NOTEBOOK.name}"
    title = "Rapamycin after stroke in aged rats: statistical analysis"
    html = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", html, count=1, flags=re.S)
    html = html.replace("</head>", f"<style>{CSS}</style>\n</head>", 1)
    html = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + NAV, html, count=1)
    html = html.replace("</body>", JS.replace("__GENERATED__", generated) + "\n</body>", 1)
    for marker in ('id="report-nav"', 'id="toggle-code"', '"code-toggle"', generated):
        assert marker in html, f"report layout was not inserted ({marker})"

    OUTPUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUTPUT.name} ({OUTPUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
