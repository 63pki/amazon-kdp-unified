"""Book configuration loading and validation from book.yaml."""

import os
from dataclasses import dataclass, field
from typing import Optional

import yaml


# Trim size definitions: (width_in, height_in, gutter_in, outside_in, top_in, bottom_in)
TRIM_SIZES = {
    '5x8':     (5.0, 8.0,   0.75,  0.5,   0.7,  0.7),
    '5.25x8':  (5.25, 8.0,  0.75,  0.5,   0.7,  0.7),
    '5.5x8.5': (5.5, 8.5,   0.875, 0.5,   0.75, 0.75),
    '6x9':     (6.0, 9.0,   0.875, 0.625, 0.8,  0.8),
    '7x10':    (7.0, 10.0,  1.0,   0.75,  0.9,  0.9),
    '8x10':    (8.0, 10.0,  1.0,   0.75,  0.9,  0.9),
}


@dataclass
class SeriesInfo:
    name: str = ''
    number: int = 0


@dataclass
class ISBNInfo:
    ebook: str = ''
    paperback: str = ''
    hardcover: str = ''
    large_print: str = ''


@dataclass
class PrintSettings:
    trim: str = '5.5x8.5'
    bleed: bool = False
    large_print_trim: str = '7x10'
    hardcover_trim: str = '6x9'


@dataclass
class Typography:
    body_font: str = 'EB Garamond'
    heading_font: str = 'EB Garamond'
    body_size: str = '11pt'
    large_print_size: str = '16pt'
    line_spacing: float = 1.3
    drop_caps: bool = True
    scene_break: str = '* * *'


@dataclass
class FrontMatterItem:
    type: str = ''
    text: str = ''
    attribution: str = ''
    extra: str = ''


@dataclass
class BackMatterItem:
    type: str = ''
    text: str = ''
    file: str = ''
    books: list = field(default_factory=list)


@dataclass
class HeaderSettings:
    left: str = '{author}'
    right: str = '{title}'


@dataclass
class BookConfig:
    title: str = 'Untitled'
    subtitle: str = ''
    author: str = 'Unknown Author'
    website: str = ''
    year: int = 2026

    series: SeriesInfo = field(default_factory=SeriesInfo)
    isbn: ISBNInfo = field(default_factory=ISBNInfo)

    manuscript: str = '.'
    chapter_pattern: str = '[0-9][0-9]_*.md'
    cover: str = ''
    output: str = 'output'
    style: str = 'default'

    print_settings: PrintSettings = field(default_factory=PrintSettings)
    typography: Typography = field(default_factory=Typography)
    headers: HeaderSettings = field(default_factory=HeaderSettings)

    front_matter: list = field(default_factory=list)
    back_matter: list = field(default_factory=list)

    # Internal: path to config file directory (for resolving relative paths)
    _config_dir: str = ''

    def resolve_path(self, path: str) -> str:
        """Resolve a path relative to the config file location."""
        if os.path.isabs(path):
            return path
        return os.path.join(self._config_dir, path)

    def get_trim(self, format_type: str = 'paperback') -> tuple:
        """Get trim size dimensions for a format type."""
        if format_type == 'large_print':
            key = self.print_settings.large_print_trim
        elif format_type == 'hardcover':
            key = self.print_settings.hardcover_trim
        else:
            key = self.print_settings.trim

        if key not in TRIM_SIZES:
            raise ValueError(
                f"Unknown trim size '{key}'. "
                f"Available: {', '.join(TRIM_SIZES.keys())}"
            )
        return TRIM_SIZES[key]

    def get_header_left(self) -> str:
        return self.headers.left.replace('{author}', self.author).replace('{title}', self.title)

    def get_header_right(self) -> str:
        return self.headers.right.replace('{author}', self.author).replace('{title}', self.title)


def load_config(path: str = 'book.yaml') -> BookConfig:
    """Load and validate a book.yaml config file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, 'r') as f:
        raw = yaml.safe_load(f) or {}

    config = BookConfig()
    config._config_dir = os.path.dirname(os.path.abspath(path))

    # Simple fields
    for key in ('title', 'subtitle', 'author', 'website', 'year',
                'manuscript', 'chapter_pattern', 'cover', 'output', 'style'):
        if key in raw:
            setattr(config, key, raw[key])

    # Nested objects
    if 'series' in raw:
        config.series = SeriesInfo(**raw['series'])

    if 'isbn' in raw:
        config.isbn = ISBNInfo(**raw['isbn'])

    if 'print' in raw:
        config.print_settings = PrintSettings(**raw['print'])

    if 'typography' in raw:
        config.typography = Typography(**raw['typography'])

    if 'headers' in raw:
        config.headers = HeaderSettings(**raw['headers'])

    # Front matter items
    if 'front_matter' in raw:
        config.front_matter = [
            FrontMatterItem(**item) for item in raw['front_matter']
        ]

    # Back matter items
    if 'back_matter' in raw:
        config.back_matter = [
            BackMatterItem(**{k: v for k, v in item.items()})
            for item in raw['back_matter']
        ]

    return config


def generate_example_config(title: str = '', author: str = '', style: str = 'default') -> str:
    """Generate an example book.yaml config file."""
    return f"""# book.yaml — Book Formatter configuration
# Docs: https://github.com/rxpelle/book-formatter

title: "{title or 'My Book Title'}"
subtitle: ""
author: "{author or 'Author Name'}"
website: ""
year: 2026

# Series information (optional)
# series:
#   name: "My Series"
#   number: 1

# Input: directory of numbered .md files, or a single .md/.docx file
manuscript: "chapters/"
chapter_pattern: "[0-9][0-9]_*.md"

# Cover image for ebook formats
# cover: "cover.jpg"

# Output directory (created automatically)
output: "output"

# Print settings
print:
  trim: "5.5x8.5"           # Options: 5x8, 5.25x8, 5.5x8.5, 6x9
  bleed: false
  large_print_trim: "7x10"  # Options: 7x10, 8x10
  hardcover_trim: "6x9"

# Typography
typography:
  body_font: "EB Garamond"
  heading_font: "EB Garamond"
  body_size: "11pt"
  large_print_size: "16pt"
  line_spacing: 1.3
  drop_caps: true
  scene_break: "* * *"      # Options: * * *, ———, ✦, or any text

# Template style
style: "{style}"              # Options: default, thriller, literary, romance

# Front matter (order determines book order)
front_matter:
  - type: "title_page"
  - type: "copyright"
  - type: "dedication"
    text: ""
  # - type: "epigraph"
  #   text: ""
  #   attribution: ""
  - type: "table_of_contents"

# Back matter
back_matter:
  - type: "author_bio"
    text: ""
  # - type: "also_by"
  #   books:
  #     - "Book Title 1"
  #     - "Book Title 2"
  # - type: "preview"
  #   file: "preview_chapter.md"

# Running headers (print only)
headers:
  left: "{{author}}"         # Verso (left/even) pages
  right: "{{title}}"         # Recto (right/odd) pages
"""