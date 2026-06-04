"""Parse .docx manuscript files into markdown for the internal Book model."""

import os
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH


def docx_to_markdown(docx_path: str) -> str:
    """Convert a .docx file to markdown text.

    Handles:
    - Headings (H1-H6) → # markers
    - Bold → **text**
    - Italic → *text*
    - Scene breaks (centered "* * *" or "---") → ---
    - Block quotes → > prefixed
    - Preserves paragraph structure
    """
    doc = Document(docx_path)
    lines = []

    for para in doc.paragraphs:
        text = para.text.strip()

        # Skip empty paragraphs (preserve as blank lines for spacing)
        if not text:
            lines.append('')
            continue

        # Handle headings
        if para.style.name.startswith('Heading'):
            level = _heading_level(para.style.name)
            lines.append(f'{"#" * level} {text}')
            lines.append('')
            continue

        # Handle centered scene breaks
        if _is_scene_break(para):
            lines.append('---')
            lines.append('')
            continue

        # Handle block quotes
        if para.style.name in ('Quote', 'Block Text', 'Intense Quote'):
            lines.append(f'> {_runs_to_markdown(para.runs)}')
            lines.append('')
            continue

        # Regular paragraph with inline formatting
        md_text = _runs_to_markdown(para.runs)
        lines.append(md_text)
        lines.append('')

    # Clean up excessive blank lines
    result = re.sub(r'\n{4,}', '\n\n\n', '\n'.join(lines))
    return result.strip() + '\n'


def _heading_level(style_name: str) -> int:
    """Extract heading level from style name like 'Heading 1'."""
    match = re.search(r'(\d+)', style_name)
    if match:
        return min(int(match.group(1)), 6)
    return 1


def _is_scene_break(para) -> bool:
    """Detect scene break paragraphs (centered *** or --- or similar)."""
    text = para.text.strip()
    if not text:
        return False

    # Common scene break patterns
    scene_break_patterns = [
        r'^\*\s*\*\s*\*$',          # * * *
        r'^\*{3,}$',                 # ***
        r'^-{3,}$',                  # ---
        r'^—{3,}$',                  # ———
        r'^[✦★◆●]{1,3}$',           # decorative markers
        r'^#$',                      # single hash (scene break marker)
    ]

    for pattern in scene_break_patterns:
        if re.match(pattern, text):
            return True

    # Also check for centered short text that looks like a break
    if para.alignment == WD_ALIGN_PARAGRAPH.CENTER and len(text) <= 5:
        if re.match(r'^[\*\-—~#✦★◆●\s]+$', text):
            return True

    return False


def _runs_to_markdown(runs) -> str:
    """Convert a paragraph's runs to markdown with inline formatting."""
    if not runs:
        return ''

    parts = []
    for run in runs:
        text = run.text
        if not text:
            continue

        if run.bold and run.italic:
            text = f'***{text}***'
        elif run.bold:
            text = f'**{text}**'
        elif run.italic:
            text = f'*{text}*'

        parts.append(text)

    result = ''.join(parts)

    # Clean up formatting artifacts from adjacent runs
    # e.g., **word****word** → **word word**
    result = re.sub(r'\*\*\*\*', ' ', result)
    result = re.sub(r'\*\*\s+\*\*', ' ', result)

    return result