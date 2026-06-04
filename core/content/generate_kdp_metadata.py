#!/usr/bin/env python3
"""
Generate Amazon KDP Publishing Metadata — kdp-metadata.json

Creates a ready-to-paste JSON file with title, subtitle, author,
HTML description, keywords, and validation against KDP rules.

Usage:
    python3 generate-kdp-metadata.py
    python3 generate-kdp-metadata.py --config /path/to/book-config.json
    python3 generate-kdp-metadata.py --project /path/to/project-dir

Output:
    {project_dir}/kdp-metadata.json
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ── KDP Constants ──────────────────────────────────────────────────────────────

MAX_DESCRIPTION_CHARS = 4000
MAX_KEYWORDS = 7
TITLE_SUBTITLE_MAX = 200

# Standard self-help/health keywords pool
COMMON_KEYWORDS = {
    "self-help": "self-help book, practical guide",
    "mental_health": "mental health, anxiety, stress management",
    "burnout": "burnout recovery, work stress, compassion fatigue",
    "women_health": "women's health, perimenopause, menopause guide",
    "chronic_illness": "chronic illness, invisible disability, chronic pain",
    "sleep": "sleep hygiene, better sleep, insomnia help",
    "caregiver": "caregiver support, caregiver burnout, family caregiving",
    "anxiety": "anxiety management, high-functioning anxiety, anxiety relief",
    "long_covid": "long covid, post-viral recovery, chronic fatigue",
    "workplace": "workplace wellness, professional development",
    "emotional_health": "emotional wellbeing, self-care routine",
    "holistic": "holistic health, mind body spirit, integrative wellness",
}

# Description templates per book type
DESCRIPTION_TEMPLATES = {
    "self-help": (
        "If you've been struggling with {topic} and feel like you've tried everything, "
        "this book is for you.\n\n"
        "<p><b>What this book offers:</b></p>"
        "<ul>"
        "<li>Honest, evidence-based insight into what's really happening</li>"
        "<li>Real strategies you can start using today</li>"
        "<li>A compassionate, non-judgmental voice throughout</li>"
        "</ul>"
        "<p>You don't need another generic to-do list. You need a guide that "
        "understands your specific situation and gives you tools that actually fit "
        "your life.</p>"
        "<p><b>Who this book is for:</b> {target_reader}</p>"
    ),
    "health_guide": (
        "<p><b>The book your doctor didn't give you.</b></p>"
        "<p>When {topic}, it's easy to feel lost, dismissed, or overwhelmed by "
        "conflicting advice. This book cuts through the noise with clear, "
        "evidence-based guidance you can actually use.</p>"
        "<p><b>Inside, you'll find:</b></p>"
        "<ul>"
        "<li>Honest explanations of what's happening in your body and mind</li>"
        "<li>Practical, immediately actionable strategies</li>"
        "<li>Real stories from people navigating the same challenges</li>"
        "</ul>"
        "<p>Written in a warm, conversational tone — no medical jargon, no "
        "guilt-tripping, no vague advice. Just real help.</p>"
        "<p><b>Ideal for:</b> {target_reader}</p>"
    ),
    "default": (
        "<p>{hook}</p>"
        "<p>This book cuts through the noise to deliver {what_it_offers}. "
        "Whether you're {target_reader}, this guide gives you the clarity and "
        "practical steps you've been looking for.</p>"
        "<p><b>What makes this different:</b> {differentiator}</p>"
        "<p><b>Perfect for:</b> {target_reader}</p>"
    ),
}


# ── Keyword Generation ───────────────────────────────────────────────────────

def generate_keywords(title: str, description: str, book_type: str = "self-help") -> list[str]:
    """
    Generate up to 7 KDP keywords based on book content.
    Keywords are ranked by relevance to the book.
    """
    title_lower = title.lower()
    desc_lower = description.lower()

    keywords = []
    seen_words = set()

    def add(keyword: str, category: str = ""):
        kw_lower = keyword.lower().strip()
        if kw_lower and kw_lower not in seen_words and len(keywords) < MAX_KEYWORDS:
            # Skip keywords already well-represented in title
            title_words = set(title_lower.split())
            if kw_lower not in title_words and kw_lower.split()[0] not in title_words:
                keywords.append(keyword.strip())
                seen_words.add(kw_lower)

    # Topic-based keywords
    topic_map = {
        "perimenopause": "perimenopause guide",
        "menopause": "menopause relief",
        "anxiety": "anxiety help",
        "burnout": "burnout recovery",
        "sleep": "sleep improvement",
        "chronic illness": "chronic illness guide",
        "long covid": "long covid recovery",
        "caregiver": "caregiver support",
        "high-functioning": "high-functioning anxiety",
    }
    for topic, kw in topic_map.items():
        if topic in title_lower or topic in desc_lower:
            add(kw)

    # Format keywords
    add("self-help book")
    add("practical guide")
    add("evidence-based")
    if book_type == "health_guide":
        add("health guide for women")
        add("holistic wellness")
    if "work" in title_lower or "professional" in desc_lower:
        add("workplace wellness")
        add("professional stress")
    if "women" in title_lower or "women" in desc_lower:
        add("women's wellness")
    if "invisible" in title_lower or "disability" in desc_lower:
        add("invisible disability")

    # If we don't have 7 yet, add from common pool
    for cat, kw_str in COMMON_KEYWORDS.items():
        if len(keywords) >= MAX_KEYWORDS:
            break
        for kw in kw_str.split(", "):
            add(kw, cat)

    return keywords[:MAX_KEYWORDS]


# ── Description Generation ───────────────────────────────────────────────────

def generate_description(
    title: str,
    topic: str,
    target_reader: str,
    book_type: str = "self-help",
    hook: str = "",
    differentiator: str = "",
    what_it_offers: str = "",
) -> str:
    """
    Generate an HTML description for KDP based on book metadata.
    """
    book_type_key = book_type.lower().replace("-", "_")
    template = DESCRIPTION_TEMPLATES.get(book_type_key, DESCRIPTION_TEMPLATES["default"])

    # Auto-generate hook if not provided
    if not hook:
        hook_map = {
            "perimenopause": "You're in your 40s. Your body feels like it's betraying you — "
                             "hot flashes, sleepless nights, mood swings you can't explain. "
                             "Your doctor says 'it's normal.' You feel anything but.",
            "anxiety": "On the outside, you've got it together. On the inside, "
                       "you're running on fumes. High-functioning anxiety is real, "
                       "exhausting, and often invisible to everyone around you.",
            "burnout": "You used to love your work. Now even Sunday evenings feel heavy. "
                       "Burnout doesn't announce itself — it sneaks up until you're running on empty.",
            "long_covid": "Everyone told you COVID was two weeks. Months later, "
                          "you're still exhausted, foggy, and nobody has answers.",
            "chronic_illness": "You look fine. You don't feel fine. Navigating an "
                               "invisible illness while the world tells you to 'push through' "
                               "is exhausting — and lonely.",
            "caregiver": "You show up for everyone else, every single day. "
                         "Who shows up for you? Caregiver burnout is real, and "
                         "you're not selfish for acknowledging it.",
        }
        for key, h in hook_map.items():
            if key in title.lower() or key in topic.lower():
                hook = h
                break
        if not hook:
            hook = (
                f"You're here because {topic}. "
                "This book is written for people like you — "
                "people who want real help, not just another list of tips "
                "that ignore how hard life already is."
            )

    if not differentiator:
        differentiator = (
            "This book is written by someone who gets it — warm, honest, "
            "and grounded in real research, not wellness trends."
        )
    if not what_it_offers:
        what_it_offers = (
            "clear explanations, practical strategies, and the kind of "
            "honest support you wish you'd had from the start"
        )

    # Format the template
    text = template.format(
        topic=topic,
        target_reader=target_reader,
        hook=hook,
        differentiator=differentiator,
        what_it_offers=what_it_offers,
    )

    return text


# ── Validation ────────────────────────────────────────────────────────────────

def validate_metadata(title: str, subtitle: str, description: str, keywords: list) -> dict:
    """
    Validate KDP metadata against rules.
    Returns a dict with validation results.
    """
    errors = []

    # Title validation
    title_invalid = (
        re.search(r"\bbestselling\b", title, re.IGNORECASE) or
        re.search(r"\bfree\b", title, re.IGNORECASE) or
        re.search(r"\bnew\b", title, re.IGNORECASE) or
        re.search(r"\bon sale\b", title, re.IGNORECASE)
    )
    if title_invalid:
        errors.append("Title contains prohibited promotional language")

    if len(title) > 150:
        errors.append(f"Title is very long ({len(title)} chars) — consider shortening")

    # Subtitle + Title combined length
    combined = (title + " " + subtitle).strip()
    if len(combined) > TITLE_SUBTITLE_MAX:
        errors.append(
            f"Title + Subtitle = {len(combined)} chars (limit: {TITLE_SUBTITLE_MAX})"
        )

    # Description validation
    desc_len = len(description)
    if desc_len > MAX_DESCRIPTION_CHARS:
        errors.append(
            f"Description = {desc_len} chars (limit: {MAX_DESCRIPTION_CHARS})"
        )
    if desc_len < 100:
        errors.append(
            f"Description is very short ({desc_len} chars) — "
            "aim for ~800-1000 for better discoverability"
        )

    # Check for emoji
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    if emoji_pattern.search(description):
        errors.append("Description contains emoji — NOT ALLOWED on KDP")

    # Check for URLs/email
    if re.search(r"https?://|www\.|\.com|\.org|@", description):
        errors.append("Description contains URL or email — NOT ALLOWED on KDP")

    # Keywords validation
    if len(keywords) > MAX_KEYWORDS:
        errors.append(f"Too many keywords ({len(keywords)}, max: {MAX_KEYWORDS})")
    if len(keywords) == 0:
        errors.append("No keywords provided — recommend adding up to 7 keywords")

    for kw in keywords:
        if '"' in kw or "'" in kw:
            errors.append(f"Keyword contains quotes: {kw}")
        if kw.lower() in ["book", "novel", "fiction", "nonfiction", "non-fiction"]:
            errors.append(f"Generic keyword not allowed: {kw}")
        if re.search(r"\b(bestselling|free|new|on sale)\b", kw, re.IGNORECASE):
            errors.append(f"Keyword contains prohibited phrase: {kw}")

    return {
        "title_valid": len([e for e in errors if "Title" in e]) == 0,
        "subtitle_length_ok": len(combined) <= TITLE_SUBTITLE_MAX,
        "description_length_ok": 100 <= desc_len <= MAX_DESCRIPTION_CHARS,
        "no_emoji": not bool(emoji_pattern.search(description)),
        "no_urls": not bool(re.search(r"https?://|www\.|\.com|\.org|@", description)),
        "keyword_count_ok": len(keywords) <= MAX_KEYWORDS,
        "description_char_count": desc_len,
        "errors": errors,
    }


# ── Main Generator ────────────────────────────────────────────────────────────

def find_config(project_dir=None) -> str | None:
    """Find book-config.json in common locations."""
    candidates = []

    if project_dir:
        p = Path(project_dir) / "book-config.json"
        if p.exists():
            candidates.append(str(p))

    # Current directory
    p = Path.cwd() / "book-config.json"
    if p.exists():
        candidates.append(str(p))

    # .workbuddy/book-projects/*/book-config.json
    for parent in [Path.cwd()] + list(Path.cwd().parents):
        wbp = parent / ".workbuddy" / "book-projects"
        if wbp.exists():
            for sub in sorted(wbp.iterdir()):
                cfg = sub / "book-config.json"
                if cfg.exists():
                    candidates.append(str(cfg))
            break

    # Script directory
    script_dir = Path(__file__).parent.resolve()
    p = script_dir / "book-config.json"
    if p.exists():
        candidates.append(str(p))

    return candidates[0] if candidates else None


def load_book_config(config_path: str) -> dict:
    """Load book config from JSON."""
    return json.loads(Path(config_path).read_text(encoding="utf-8"))


def generate_kdp_metadata(config: dict) -> dict:
    """
    Generate full KDP metadata from book config.
    """
    title = config.get("title", "")
    subtitle = config.get("subtitle", "")
    author = config.get("author", "Author Name")
    description_plain = config.get("description", "")
    target_reader = config.get("target_audience", "anyone struggling with this topic")
    topic = config.get("topic", title)
    book_type = config.get("book_type", "self-help")
    hook = config.get("hook", "")
    differentiator = config.get("differentiator", "")
    what_it_offers = config.get("what_it_offers", "")
    kdp_select = config.get("kdp_select", False)
    publisher = config.get("publisher", "")

    # Determine hook/differentiator from book type
    if not hook:
        hook_map = {
            "perimenopause": "You're in your 40s. Your body feels like it's betraying you — hot flashes, sleepless nights, mood swings you can't explain. Your doctor says 'it's normal.' You feel anything but.",
            "anxiety": "On the outside, you've got it together. On the inside, you're running on fumes. High-functioning anxiety is real, exhausting, and often invisible to everyone around you.",
            "burnout": "You used to love your work. Now even Sunday evenings feel heavy. Burnout doesn't announce itself — it sneaks up until you're running on empty.",
            "long_covid": "Everyone told you COVID was two weeks. Months later, you're still exhausted, foggy, and nobody has answers.",
            "chronic_illness": "You look fine. You don't feel fine. Navigating an invisible illness while the world tells you to 'push through' is exhausting — and lonely.",
            "caregiver": "You show up for everyone else, every single day. Who shows up for you? Caregiver burnout is real, and you're not selfish for acknowledging it.",
        }
        for key, h in hook_map.items():
            if key in title.lower() or key in topic.lower():
                hook = h
                break

    # Generate HTML description
    html_description = generate_description(
        title=title,
        topic=topic,
        target_reader=target_reader,
        book_type=book_type,
        hook=hook,
        differentiator=differentiator,
        what_it_offers=what_it_offers,
    )

    # Generate keywords
    keywords = generate_keywords(
        title=title,
        description=html_description,
        book_type=book_type,
    )

    # Validate
    validation = validate_metadata(title, subtitle, html_description, keywords)

    return {
        "title": title,
        "subtitle": subtitle,
        "author": author,
        "description": {
            "html": html_description,
            "plain": description_plain,
            "char_count": validation["description_char_count"],
        },
        "keywords": keywords,
        "categories": config.get("categories", []),
        "language": config.get("language", "English"),
        "primary_audience": target_reader,
        "publisher": publisher,
        "isbn": None,
        "rights": "owned",
        "kdp_select": kdp_select,
        "book_type": book_type,
        "validation": validation,
        "_generated_by": "generate-kdp-metadata.py",
        "_config_source": "book-config.json",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate Amazon KDP publishing metadata from book-config.json"
    )
    parser.add_argument("--config", default=None,
                        help="Path to book-config.json")
    parser.add_argument("--project", default=None,
                        help="Project directory containing book-config.json")
    parser.add_argument("--interactive", action="store_true",
                        help="Run in interactive mode to customize metadata")
    args = parser.parse_args()

    # Find config
    config_path = args.config
    if not config_path:
        config_path = find_config(project_dir=args.project)
        if not config_path:
            print("ERROR: No book-config.json found.")
            print("  Searched: ./book-config.json, .workbuddy/book-projects/*/book-config.json")
            print("\n  Run setup-book.py first to create a book project.")
            sys.exit(1)
    print(f"Using config: {config_path}")

    config = load_book_config(config_path)
    project_dir = Path(config_path).parent.resolve()

    # Generate metadata
    kdp = generate_kdp_metadata(config)

    # Interactive mode: let user customize
    if args.interactive:
        print("\n📋 KDP Metadata — Interactive Editor")
        print("=" * 50)
        print(f"\n1. Title [{len(kdp['title'])} chars]:\n   {kdp['title']}")
        new_title = input("   [Enter to keep] > ").strip()
        if new_title:
            kdp["title"] = new_title

        print(f"\n2. Subtitle [{len(kdp.get('subtitle',''))} chars]:\n   {kdp.get('subtitle','')}")
        new_sub = input("   [Enter to keep] > ").strip()
        if new_sub != "":
            kdp["subtitle"] = new_sub

        print(f"\n3. Author:\n   {kdp['author']}")
        new_author = input("   [Enter to keep] > ").strip()
        if new_author:
            kdp["author"] = new_author

        print(f"\n4. Keywords ({len(kdp['keywords'])}/7):")
        for i, kw in enumerate(kdp["keywords"], 1):
            print(f"   {i}. {kw}")
        print("   [Enter to keep current list, or type keywords one by line]")
        kw_input = []
        while len(kw_input) < MAX_KEYWORDS:
            kw = input(f"   Keyword {len(kw_input)+1} [Enter to stop]: ").strip()
            if not kw:
                break
            kw_input.append(kw)
        if kw_input:
            kdp["keywords"] = kw_input

        print(f"\n5. Description [{kdp['description']['char_count']} chars]:")
        print("   [Showing first 300 chars]")
        print("   " + kdp["description"]["html"][:300].replace("\n", " ") + "...")
        print("   [Use --interactive to edit description interactively]")
        _ = input("   [Enter to continue] > ")

        # Re-validate
        kdp["validation"] = validate_metadata(
            kdp["title"], kdp.get("subtitle", ""),
            kdp["description"]["html"], kdp["keywords"]
        )

    # Save output
    output_path = project_dir / "kdp-metadata.json"
    output_path.write_text(
        json.dumps(kdp, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )
    print(f"\n✅ Generated: {output_path}")

    # Print validation results
    v = kdp["validation"]
    print(f"\n📊 Validation ({len(v['errors'])} issue(s)):")
    if v["errors"]:
        for err in v["errors"]:
            print(f"  ⚠  {err}")
    else:
        print("  ✅ All checks passed!")

    print(f"\n📋 KDP Metadata Summary:")
    print(f"  Title:       {kdp['title']}")
    if kdp.get("subtitle"):
        print(f"  Subtitle:    {kdp['subtitle']}")
    print(f"  Author:      {kdp['author']}")
    print(f"  Description: {v['description_char_count']} chars")
    print(f"  Keywords:    {', '.join(kdp['keywords'])}")
    print(f"  KDP Select:  {'Yes (exclusive)' if kdp['kdp_select'] else 'No (non-exclusive)'}")

    print(f"\nNext steps:")
    print(f"  1. Review kdp-metadata.json")
    print(f"  2. Copy description HTML to KDP book description field")
    print(f"  3. Enter keywords on KDP (copy one per box)")
    print(f"  4. Run merge-book.py to generate the book HTML/PDF")
    print(f"     python3 {Path(__file__).resolve()}")


if __name__ == "__main__":
    main()