"""Config stub for youngReader agent compatibility."""
import os
from dataclasses import dataclass, field
from typing import Optional

DEFAULT_MODEL = os.getenv("LLM_MODEL", "claude-opus-4-5")
MAX_RETRIES = 3

@dataclass
class GenerationConfig:
    model: str = DEFAULT_MODEL
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    system_prompt: Optional[str] = None
    seed: Optional[int] = None

@dataclass 
class BookConfig:
    title: str = ""
    genre: str = ""
    target_audience: str = ""
    chapter_count: int = 10
    words_per_chapter: int = 2000
    generation: GenerationConfig = field(default_factory=GenerationConfig)
