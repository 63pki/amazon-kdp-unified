"""Internal document model for parsed manuscripts."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Chapter:
    number: int
    title: str
    content: str  # Raw markdown content
    source_file: str = ''
    word_count: int = 0
    is_epilogue: bool = False
    is_preview: bool = False
    is_unnumbered: bool = False  # For prologue, epilogue, etc.


@dataclass
class Book:
    chapters: list[Chapter] = field(default_factory=list)
    word_count: int = 0
    estimated_pages: int = 0  # ~250 words/page for standard, ~200 for large print

    def calculate_stats(self, words_per_page: int = 250):
        """Calculate aggregate stats from chapters."""
        self.word_count = sum(ch.word_count for ch in self.chapters)
        self.estimated_pages = max(1, self.word_count // words_per_page)