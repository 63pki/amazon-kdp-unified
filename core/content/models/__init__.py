"""Stub models for youngReader agent compatibility."""
from dataclasses import dataclass, field
from typing import List, Optional, Any

@dataclass
class Scene:
    title: str = ""
    content: str = ""

@dataclass
class ChapterPlan:
    title: str = ""
    scenes: List[Scene] = field(default_factory=list)
    summary: str = ""

@dataclass
class Character:
    name: str = ""
    description: str = ""
    role: str = ""

@dataclass
class Chapter:
    title: str = ""
    content: str = ""
    number: int = 0

@dataclass
class Book:
    title: str = ""
    author: str = ""
    chapters: List[Chapter] = field(default_factory=list)
    characters: List[Character] = field(default_factory=list)
