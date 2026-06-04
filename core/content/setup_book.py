#!/usr/bin/env python3
"""
Book Setup Wizard — Interactive book project creator.

Usage:
    python3 setup-book.py
    python3 setup-book.py --from book-writing-projects.md --book perimenopause
"""

import argparse
import json
import re
import sys
from pathlib import Path


def slugify(title: str) -> str:
    """Convert title to URL-friendly slug."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def find_book_projects_md() -> Path | None:
    """Find book-writing-projects.md in common locations."""
    candidates = [
        Path.cwd() / ".workbuddy" / "book-projects" / "book-writing-projects.md",
        Path.home() / ".workbuddy" / "book-projects" / "book-writing-projects.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def parse_book_projects(md_path: Path) -> list[dict]:
    """Parse book-writing-projects.md into a list of book ideas."""
    text = md_path.read_text(encoding="utf-8")
    books = []
    current = None

    for line in text.splitlines():
        m = re.match(r"## Book #\d+\s+(.+)$", line)
        if m:
            if current:
                books.append(current)
            current = {"title": m.group(1).strip(), "details": ""}
        elif current is not None:
            current["details"] += line + "\n"
    if current:
        books.append(current)

    return books


def interactive_setup() -> dict:
    """Interactive Q&A to gather book metadata."""
    print("\n📚 Book Project Setup Wizard\n" + "-" * 40)

    title = input("Book title (working title): ").strip()
    if not title:
        print("ERROR: Title is required.")
        sys.exit(1)

    subtitle = input("Subtitle (optional): ").strip()
    author = input("Author name: ").strip() or "Author"
    topic = input("Core topic/problem the book addresses: ").strip() or title
    target_audience = input("Target reader (who is this for?): ").strip() or "anyone struggling with this topic"

    print("\nBook type:")
    print("  [1] self-help (default)")
    print("  [2] health-guide (for medical/health topics)")
    book_type_choice = input("Choice [1]: ").strip() or "1"
    book_type = "health-guide" if book_type_choice == "2" else "self-help"

    description = input("One-line description: ").strip() or ""

    print("\nChapters (enter one per line, blank line to finish):")
    chapters = []
    toc_items = []
    while True:
        ch = input(f"  Chapter {len(chapters)+1} title: ").strip()
        if not ch:
            break
        slug = slugify(ch)
        fname = f"ch{len(chapters)+1:02d}-{slug}.md"
        chapters.append(fname)
        toc_items.append(ch)

    cover = input("Cover image path (optional): ").strip()
    kdp_select = input("KDP Select (exclusive to Amazon)? [y/N]: ").strip().lower() == "y"
    publisher = input("Publisher name for KDP (optional): ").strip()

    slug = slugify(title)
    workspace = input(f"Project directory [{slug}/]: ").strip()
    if not workspace:
        workspace = slug

    return {
        "title": title,
        "subtitle": subtitle,
        "author": author,
        "topic": topic,
        "target_audience": target_audience,
        "book_type": book_type,
        "description": description,
        "chapters": chapters,
        "toc_items": toc_items,
        "cover_image": cover,
        "workspace": workspace,
        "slug": slug,
        "kdp_select": kdp_select,
        "publisher": publisher,
        "categories": [],
        "language": "English",
    }


def from_existing_project(md_path: Path, book_keyword: str) -> dict:
    """Create config from an existing book idea in book-writing-projects.md."""
    books = parse_book_projects(md_path)
    if not books:
        print(f"ERROR: No book projects found in {md_path}")
        sys.exit(1)

    # Find matching book
    match = None
    for b in books:
        if book_keyword.lower() in b["title"].lower():
            match = b
            break

    if not match:
        print(f"\nAvailable books:")
        for i, b in enumerate(books):
            print(f"  [{i+1}] {b['title']}")
        choice = input("\nSelect book [1]: ").strip() or "1"
        match = books[int(choice) - 1]

    title = match["title"]
    slug = slugify(title)
    topic = match.get("details", "").strip()[:80] or title

    print(f"\n📖 Selected: {title}")
    subtitle = input("Subtitle (optional): ").strip()
    author = input("Author name: ").strip() or "Author"
    target_audience = input("Target reader: ").strip() or "anyone struggling with this topic"
    description = input("One-line description: ").strip() or ""

    print("\nBook type:")
    print("  [1] self-help (default)")
    print("  [2] health-guide")
    book_type_choice = input("Choice [1]: ").strip() or "1"
    book_type = "health-guide" if book_type_choice == "2" else "self-help"

    # Extract chapter ideas from details
    details = match.get("details", "")
    suggested_chapters = re.findall(r"[-*]\s*\*\*(.+?)\*\*", details)
    if not suggested_chapters:
        suggested_chapters = re.findall(r"[-*]\s*(.+)", details)[:10]

    chapters = []
    toc_items = []
    if suggested_chapters:
        print(f"\nSuggested chapters from project file:")
        for i, ch in enumerate(suggested_chapters):
            print(f"  {i+1}. {ch}")
        use = input("\nUse these chapters? [Y/n]: ").strip().lower()
        if use != "n":
            for i, ch in enumerate(suggested_chapters):
                ch_slug = slugify(ch)
                fname = f"ch{i+1:02d}-{ch_slug}.md"
                chapters.append(fname)
                toc_items.append(ch)

    if not chapters:
        print("\nEnter chapters manually (blank line to finish):")
        while True:
            ch = input(f"  Chapter {len(chapters)+1} title: ").strip()
            if not ch:
                break
            ch_slug = slugify(ch)
            fname = f"ch{len(chapters)+1:02d}-{ch_slug}.md"
            chapters.append(fname)
            toc_items.append(ch)

    kdp_select = input("KDP Select (exclusive to Amazon)? [y/N]: ").strip().lower() == "y"
    publisher = input("Publisher name (optional): ").strip()

    workspace = slug
    return {
        "title": title,
        "subtitle": subtitle,
        "author": author,
        "topic": topic,
        "target_audience": target_audience,
        "book_type": book_type,
        "description": description,
        "chapters": chapters,
        "toc_items": toc_items,
        "cover_image": "",
        "workspace": workspace,
        "slug": slug,
        "kdp_select": kdp_select,
        "publisher": publisher,
        "categories": [],
        "language": "English",
    }


def create_project_files(data: dict):
    """Create project directory and all necessary files."""
    ws = Path(data["workspace"]).expanduser().resolve()
    ws.mkdir(parents=True, exist_ok=True)
    chapters_dir = ws / "chapters"
    chapters_dir.mkdir(exist_ok=True)
    output_dir = ws / (data.get("output_dir") or "Book-Output")
    output_dir.mkdir(exist_ok=True)

    # Write book-config.json (full KDP-ready config)
    config = {
        "workspace": ".",
        "chapters_dir": "chapters",
        "output_dir": "Book-Output",
        "cover_image": data.get("cover_image", ""),
        "chapters": data["chapters"],
        "title": data["title"],
        "subtitle": data.get("subtitle", ""),
        "author": data["author"],
        "topic": data.get("topic", data["title"]),
        "target_audience": data.get("target_audience", ""),
        "book_type": data.get("book_type", "self-help"),
        "description": data.get("description", ""),
        "kdp_select": data.get("kdp_select", False),
        "publisher": data.get("publisher", ""),
        "categories": data.get("categories", []),
        "language": data.get("language", "English"),
        "toc_items": data["toc_items"],
        "slug": data["slug"],
    }
    config_path = ws / "book-config.json"
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )
    print(f"\n✅ Created: {config_path}")

    # Write outline.md
    outline_path = ws / "outline.md"
    if not outline_path.exists():
        lines = [
            f"# {data['title']} — Content Outline\n",
            f"**Subtitle:** {data.get('subtitle', '')}\n",
            f"**Author:** {data['author']}\n",
            f"**Description:** {data.get('description', '')}\n",
            "\n---\n",
        ]
        for i, (ch, toc) in enumerate(zip(data["chapters"], data["toc_items"]), 1):
            lines.append(f"\n## Chapter {i}: {toc}\n")
            lines.append(f"- [ ] Key point 1\n")
            lines.append(f"- [ ] Key point 2\n")
            lines.append(f"- [ ] Key point 3\n")
            lines.append(f"- Target: 800-1200 words\n")
        outline_path.write_text("".join(lines), encoding="utf-8")
        print(f"✅ Created: {outline_path}")

    # Create sample chapter template
    sample_path = chapters_dir / data["chapters"][0]
    if not sample_path.exists():
        tmpl = f"""# Chapter 1: {data['toc_items'][0] if data['toc_items'] else 'Introduction'}

{{{{ Opening hook — draw the reader in with a relatable scenario or surprising fact. }}}}

## The Core Problem

{{{{ Explain what's happening and why it matters. }}}}

## What the Research Says

{{{{ Evidence-based insights, keep it conversational. }}}}

## What You Can Do

1. **First action step** — concrete and specific.
2. **Second action step** — something they can do this week.

> **Key Takeaway:** {{{{ one-sentence summary }}}}

**Chapter Summary:**
{{{{ 2-3 sentences recapping the chapter. }}}}

**What to do this week:**
1. {{{{ specific action }}}}
2. {{{{ specific action }}}}
"""
        sample_path.write_text(tmpl, encoding="utf-8")
        print(f"✅ Created sample chapter: {sample_path}")

    skill_dir = Path(__file__).resolve().parent.parent
    print(f"\n📁 Project directory: {ws}")
    print(f"📄 Config: {config_path.name}")
    print(f"📝 Outline: {outline_path.name}")
    print(f"📂 Chapters: {chapters_dir}")
    print(f"\nNext steps:")
    print(f"  1. Edit outline.md to refine chapter topics")
    print(f"  2. Write chapters in {chapters_dir}/")
    print(f"  3. Generate KDP metadata:")
    print(f"     python3 {skill_dir}/scripts/generate-kdp-metadata.py --project {ws}")
    print(f"  4. Run merge-book.py to generate HTML + PDF:")
    print(f"     python3 {skill_dir}/scripts/merge-book.py --project {ws}")


def main():
    parser = argparse.ArgumentParser(description="Book project setup wizard.")
    parser.add_argument("--from", dest="md_file", default=None,
                        help="Path to book-writing-projects.md")
    parser.add_argument("--book", default=None,
                        help="Keyword to match book title in the md file")
    args = parser.parse_args()

    if args.md_file or args.book:
        md_path = Path(args.md_file) if args.md_file else find_book_projects_md()
        if not md_path or not md_path.exists():
            print("ERROR: book-writing-projects.md not found.")
            print("  Searched: .workbuddy/book-projects/book-writing-projects.md")
            sys.exit(1)
        data = from_existing_project(md_path, args.book or "")
    else:
        data = interactive_setup()

    print(f"\n📋 Review your book config:")
    print(f"  Title:       {data['title']}")
    print(f"  Subtitle:    {data.get('subtitle', '')}")
    print(f"  Author:      {data['author']}")
    print(f"  Chapters:    {len(data['chapters'])}")
    print(f"  Workspace:   {data['workspace']}")
    confirm = input("\nCreate project? [Y/n]: ").strip().lower()
    if confirm == "n":
        print("Cancelled.")
        sys.exit(0)

    create_project_files(data)


if __name__ == "__main__":
    main()