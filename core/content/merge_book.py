#!/usr/bin/env python3
"""
Book Merger — Merge Markdown chapters into a complete HTML + PDF book.

Usage:
    python3 merge-book.py                          # auto-find book-config.json
    python3 merge-book.py --config /path/to/config.json   # manual config path
    python3 merge-book.py --project /path/to/project      # specify project dir

Config auto-discovery (in order):
  1. --config flag (if provided)
  2. --project flag (look for book-config.json in that dir)
  3. ./book-config.json (current directory)
  4. .workbuddy/book-projects/*/book-config.json (all subdirs)
  5. Script directory's book-config.json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ── Default config ────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "workspace": ".",
    "chapters_dir": "chapters",
    "output_dir": "Book-Output",
    "cover_image": "",
    "chapters": [],
    "title": "Book Title",
    "subtitle": "The Book Subtitle",
    "author": "Author Name",
    "description": "A practical, evidence-based guide.",
    "toc_items": [],
    "slug": "",
}


# ── Config auto-discovery ─────────────────────────────────────────────────────

def find_config(project_dir=None) -> str | None:
    """
    Auto-discover book-config.json.
    Returns the path to the config file, or None if not found.
    """
    candidates = []

    # 1. project_dir/book-config.json (if --project given)
    if project_dir:
        p = Path(project_dir).expanduser().resolve() / "book-config.json"
        if p.exists():
            candidates.append(str(p))

    # 2. ./book-config.json (current working directory)
    p = Path.cwd() / "book-config.json"
    if p.exists():
        candidates.append(str(p))

    # 3. .workbuddy/book-projects/*/book-config.json
    wb_root = Path.cwd()
    # Look for .workbuddy in current dir or any parent
    for parent in [wb_root] + list(wb_root.parents):
        wbp = parent / ".workbuddy" / "book-projects"
        if wbp.exists():
            for sub in sorted(wbp.iterdir()):
                cfg = sub / "book-config.json"
                if cfg.exists():
                    candidates.append(str(cfg))
            break

    # 4. Script directory's book-config.json
    script_dir = Path(__file__).parent.resolve()
    p = script_dir / "book-config.json"
    if p.exists():
        candidates.append(str(p))

    if not candidates:
        return None

    if len(candidates) == 1:
        return candidates[0]

    # Multiple found — list them and ask user to choose
    print("\nMultiple book-config.json files found:")
    for i, c in enumerate(candidates):
        print(f"  [{i+1}] {c}")
    print()
    while True:
        try:
            choice = input("Select config [1]: ").strip() or "1"
            idx = int(choice) - 1
            if 0 <= idx < len(candidates):
                return candidates[idx]
        except (ValueError, IndexError):
            print(f"  Please enter a number between 1 and {len(candidates)}")
        except EOFError:
            # Non-interactive mode — use the first one and warn
            print(f"  Non-interactive mode: using [1] {candidates[0]}\n")
            return candidates[0]


# ── Markdown → HTML ───────────────────────────────────────────────────────────

def md_to_html(text: str) -> str:
    """Convert basic Markdown to HTML."""
    html = (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;"))

    # Code blocks (```lang\n...```)
    html = re.sub(r"```(\w*)\n(.*?)```", r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
    # Inline code
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

    # Headers — handles start-of-file AND mid-text
    for lvl in [1, 2, 3, 4]:
        hashes = "#" * lvl
        html = re.sub(
            rf"(?:^|\n){hashes} (.+?)(?:\n|$)",
            lambda m: f"\n<h{lvl}>{m.group(1).strip()}</h{lvl}>\n",
            html,
            flags=re.MULTILINE
        )

    # Bold / Italic
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # HR
    html = re.sub(r"\n---+\n", "\n<hr>\n", html)

    # Blockquote
    html = re.sub(r"\n> (.+)", r"<p><em>\1</em></p>", html)

    # Unordered lists
    html = re.sub(r"(^[-*] .+$\n?)+", lambda m: (
        "<ul>" +
        re.sub(r"^[-*] (.+)$", r"<li>\1</li>", m.group(), flags=re.MULTILINE) +
        "</ul>"
    ), html, flags=re.MULTILINE)

    # Ordered lists
    html = re.sub(r"(^\d+\. .+$\n?)+", lambda m: (
        "<ol>" +
        re.sub(r"^\d+\. (.+)$", r"<li>\1</li>", m.group(), flags=re.MULTILINE) +
        "</ol>"
    ), html, flags=re.MULTILINE)

    # Tables
    html = _convert_tables(html)

    # Paragraphs — wrap remaining text blocks (skip already-tagged lines)
    html = re.sub(r"\n([^<\n][^\n]+)\n\n", r"\n<p>\1</p>\n", html)

    return html


def _convert_tables(text: str) -> str:
    """Convert simple Markdown tables to HTML tables."""
    table_pattern = re.compile(
        r"(\|.+\|\n\|[-| :]+\|\n)((?:\|.+\|\n)+)",
        re.MULTILINE
    )

    def build_table(m):
        rows = m.group(2).strip().split("\n")
        header = rows[0] if rows else ""
        body_rows = rows[1:] if len(rows) > 1 else []

        def row_to_cells(row, tag):
            cells = [c.strip() for c in row.strip("|").split("|")]
            # Strip any markdown heading markers that leaked into table cells
            cells = [re.sub(r"^#{1,4}\s+", "", c) for c in cells]
            return "".join(f"<{tag}>{c}</{tag}>" for c in cells)

        header_html = f"<thead><tr>{row_to_cells(header, 'th')}</tr></thead>"
        body_html = "<tbody>"
        for r in body_rows:
            body_html += f"<tr>{row_to_cells(r, 'td')}</tr>"
        body_html += "</tbody>"

        return f"<table>{header_html}{body_html}</table>"

    return table_pattern.sub(build_table, text)


# ── HTML Document Builder ─────────────────────────────────────────────────────

def build_full_html(chapters_html: list[str], config: dict) -> str:
    """Wrap chapters in a complete HTML document."""
    cover_img = config.get("cover_image", "")
    title = config.get("title", "Book Title")
    subtitle = config.get("subtitle", "")
    author = config.get("author", "")
    description = config.get("description", "")
    toc_items = config.get("toc_items", [])

    chapters_str = "\n".join(chapters_html)

    cover_img_tag = (
        f'<img src="{cover_img}" '
        'alt="Cover" '
        'style="width:55%; max-width:380px; display:block; margin:0 auto 1.5rem;'
        'border-radius:4px; box-shadow:0 4px 20px rgba(0,0,0,0.12);" />'
        if cover_img else ""
    )

    toc_rows = "".join(
        f"    <li><span>{item}</span></li>\n"
        for item in toc_items
    )

    back_cover_img_tag = (
        f'<img src="{cover_img}" alt="Cover" '
        'style="width:40%; max-width:280px; border-radius:4px;'
        'box-shadow:0 4px 16px rgba(0,0,0,0.12); margin:0 auto 2rem; display:block;" />'
        if cover_img else ""
    )

    # When cover image exists, hide title/subtitle on cover page (redundant with image)
    has_cover_cls = " has-cover" if cover_img else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 11pt;
    line-height: 1.75;
    color: #2c2c2c;
    background: #fff;
    max-width: 700px;
    margin: 0 auto;
    padding: 3rem 2rem 6rem;
  }}

  /* Cover Page */
  .cover {{
    text-align: center;
    padding: 4rem 0 3rem;
    border-bottom: 2px solid #2c2c2c;
    margin-bottom: 3rem;
  }}
  .cover-title {{
    font-size: 2.4rem;
    font-weight: bold;
    letter-spacing: -0.5px;
    line-height: 1.2;
    color: #1a1a2e;
    margin: 1.5rem 0 0.5rem;
  }}
  .cover-subtitle {{
    font-size: 1.1rem;
    color: #555;
    font-style: italic;
    margin-bottom: 2rem;
  }}
  .cover-note {{
    font-size: 0.85rem;
    color: #888;
    margin-top: 2rem;
  }}
  /* When cover image is present, hide the redundant title/subtitle on cover page */
  .cover.has-cover .cover-title,
  .cover.has-cover .cover-subtitle {{
    display: none;
  }}

  /* TOC */
  .toc {{
    page-break-after: always;
    margin-bottom: 3rem;
  }}
  .toc h2 {{
    font-size: 1.4rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid #ccc;
    padding-bottom: 0.3rem;
  }}
  .toc ol {{ counter-reset: chapter; list-style: none; padding-left: 0; }}
  .toc li {{
    counter-increment: chapter;
    margin: 0.4rem 0;
    display: flex;
    justify-content: space-between;
    font-size: 1rem;
  }}
  .toc li::before {{
    content: counter(chapter) ". ";
    font-weight: bold;
    min-width: 2rem;
  }}
  .toc li span {{ flex: 1; padding-left: 0.5rem; }}

  /* Chapter headings */
  h1 {{
    font-size: 1.8rem;
    margin: 2.5rem 0 1.5rem;
    color: #1a1a2e;
    border-bottom: 3px solid #e8a0bf;
    padding-bottom: 0.4rem;
    page-break-before: always;
  }}
  h2 {{
    font-size: 1.25rem;
    margin: 2rem 0 0.8rem;
    color: #2a2a5e;
    font-weight: bold;
  }}
  h3 {{
    font-size: 1.05rem;
    margin: 1.5rem 0 0.5rem;
    color: #333;
    font-weight: bold;
  }}

  /* Body text */
  p {{ margin: 0 0 1rem; orphans: 3; widows: 3; }}
  .lead {{
    font-size: 1.15rem;
    color: #444;
    line-height: 1.6;
    margin-bottom: 1.5rem;
  }}

  /* Lists */
  ul, ol {{ margin: 0.5rem 0 1rem 1.5rem; }}
  li {{ margin: 0.25rem 0; }}

  /* Blockquote */
  blockquote, p > em {{
    border-left: 4px solid #e8a0bf;
    margin: 1.5rem 0;
    padding: 0.8rem 1.2rem;
    background: #fdf4f8;
    font-style: italic;
  }}

  /* Tables */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1.2rem 0;
    font-size: 0.9rem;
  }}
  th {{
    background: #2a2a5e;
    color: #fff;
    padding: 0.5rem 0.7rem;
    text-align: left;
    font-weight: bold;
  }}
  td {{
    padding: 0.4rem 0.7rem;
    border-bottom: 1px solid #e0e0e0;
  }}
  tr:nth-child(even) td {{ background: #f9f4f9; }}

  /* Chapter break */
  .chapter-end {{
    text-align: center;
    margin: 2.5rem 0;
    color: #ccc;
    font-size: 1.5rem;
    letter-spacing: 0.5rem;
  }}

  /* Action box */
  .action-box {{
    background: #f0f4ff;
    border: 2px solid #4a6fa5;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    margin: 1.5rem 0;
  }}
  .action-box strong {{ color: #2a2a5e; display: block; margin-bottom: 0.4rem; }}

  /* Print styles */
  @media print {{
    h1 {{ page-break-before: always; }}
    .cover {{ page-break-after: always; }}
  }}
</style>
</head>
<body>

<!-- ══ COVER ═════════════════════════════════════════════════ -->
<div class="cover{has_cover_cls}">
  {cover_img_tag}
  <div class="cover-title">{title}</div>
  <div class="cover-subtitle">{subtitle}</div>
  <p style="color:#666; font-size:1rem; max-width:480px; margin:0 auto 1.5rem;
             font-style:italic; line-height:1.6;">
    {description}
  </p>
  <p class="cover-note">{author}</p>
</div>

<!-- ══ TABLE OF CONTENTS ══════════════════════════════════════ -->
<div class="toc">
  <h2>Contents</h2>
  <ol>
{toc_rows}  </ol>
</div>

<!-- ══ CHAPTERS ════════════════════════════════════════════════ -->
{chapters_str}

<!-- ══ BACK COVER ══════════════════════════════════════════════ -->
<div style="page-break-before:always; text-align:center; padding:4rem 0;
             border-top:2px solid #2c2c2c; margin-top:3rem;">
  <p style="font-size:1.3rem; font-weight:bold; color:#1a1a2e;
             margin-bottom:1rem;">{title}</p>
  <p style="font-size:1rem; color:#555; font-style:italic; margin-bottom:2rem;">
    {subtitle}
  </p>
  {back_cover_img_tag}
  <p style="font-size:0.85rem; color:#888; max-width:400px; margin:0 auto;
             line-height:1.6;">
    This book is for informational purposes and does not constitute medical advice.
    Always consult a qualified healthcare provider for diagnosis and treatment.
  </p>
</div>

</body>
</html>"""


# ── Config Loader ──────────────────────────────────────────────────────────────

def load_config(config_path: str) -> dict:
    """Load and merge config file with defaults."""
    path = Path(config_path)
    if not path.exists():
        print(f"Config not found: {config_path}")
        sys.exit(1)

    user_config = json.loads(path.read_text(encoding="utf-8"))
    cfg = {**DEFAULT_CONFIG, **user_config}

    # Resolve paths relative to config file's directory
    base = path.parent.resolve()
    ws = (base / cfg["workspace"]).resolve()

    cfg["_workspace"] = ws
    cfg["_chapters_dir"] = (
        (base / cfg["chapters_dir"]).resolve()
        if not Path(cfg["chapters_dir"]).is_absolute()
        else Path(cfg["chapters_dir"])
    )
    cfg["_output_dir"] = (
        (base / cfg["output_dir"]).resolve()
        if not Path(cfg["output_dir"]).is_absolute()
        else Path(cfg["output_dir"])
    )
    if cfg.get("cover_image"):
        cfg["cover_image"] = str(
            (base / cfg["cover_image"]).resolve()
            if not Path(cfg["cover_image"]).is_absolute()
            else Path(cfg["cover_image"])
        )

    slug = cfg.get("slug", "").strip()
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", cfg["title"].lower()).strip("-")
    cfg["_slug"] = slug

    return cfg


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Merge Markdown chapters into HTML + PDF book."
    )
    parser.add_argument("--config", default=None,
                        help="Path to book-config.json (default: auto-discover)")
    parser.add_argument("--project", default=None,
                        help="Project directory containing book-config.json")
    args = parser.parse_args()

    # Find config
    config_path = None
    if args.config:
        config_path = args.config
        print(f"Using config: {config_path}")
    else:
        config_path = find_config(project_dir=args.project)
        if not config_path:
            print("ERROR: No book-config.json found.")
            print("\nSearched:")
            print("  1. --project <dir>/book-config.json")
            print("  2. ./book-config.json")
            print("  3. .workbuddy/book-projects/*/book-config.json")
            print("  4. Script directory/book-config.json")
            print("\nTip: Run 'python3 setup-book.py' to create a new book project.")
            sys.exit(1)
        print(f"Found config: {config_path}")

    cfg = load_config(config_path)

    ws = cfg["_workspace"]
    chapters_dir = cfg["_chapters_dir"]
    output_dir = cfg["_output_dir"]
    output_dir.mkdir(exist_ok=True, parents=True)

    print(f"\nWorkspace:  {ws}")
    print(f"Chapters:   {chapters_dir}")
    print(f"Output:     {output_dir}")
    print()

    # 1. Convert all chapters
    chapters_html = []
    for fname in cfg["chapters"]:
        path = chapters_dir / fname
        if path.exists():
            html = md_to_html(path.read_text(encoding="utf-8"))
            chapters_html.append(html)
            print(f"  ✓ {fname}")
        else:
            print(f"  ✗ MISSING: {fname}")

    if not chapters_html:
        print("\nNo chapters found. Check your config.")
        sys.exit(1)

    # 2. Build HTML
    full_html = build_full_html(chapters_html, cfg)
    html_path = output_dir / f"{cfg['_slug']}.html"
    html_path.write_text(full_html, encoding="utf-8")
    print(f"\n  HTML → {html_path}")

    # 3. Generate PDF via Playwright
    try:
        from playwright.sync_api import sync_playwright

        pdf_path = output_dir / f"{cfg['_slug']}.pdf"
        print(f"\n  Generating PDF with Playwright...")

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{html_path.resolve()}", wait_until="networkidle")
            page.pdf(
                path=str(pdf_path),
                format="A4",
                margin={"top": "2cm", "bottom": "2cm",
                        "left": "2.5cm", "right": "2.5cm"},
                print_background=True,
                display_header_footer=False,
            )
            browser.close()

        print(f"  PDF → {pdf_path}")

    except ImportError:
        print("\n  ⚠ Playwright not installed. Install with:")
        print("    pip install playwright && playwright install chromium")
        print("  HTML was generated; re-run after installing to get PDF.")

    print(f"\n✅ Done!")
    print(f"   HTML: {html_path}")
    if "pdf_path" in dir():
        print(f"   PDF:  {pdf_path}")


if __name__ == "__main__":
    main()