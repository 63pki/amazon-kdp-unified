"""Base generator with shared Pandoc invocation logic."""

import os
import shutil
import subprocess
import tempfile

from rich.console import Console

from book_formatter.config import BookConfig
from book_formatter.parsers.ast_model import Book

console = Console()


class GeneratorError(Exception):
    """Raised when a generator fails."""
    pass


class BaseGenerator:
    """Base class for all format generators."""

    format_name: str = 'unknown'
    file_extension: str = ''

    def __init__(self, config: BookConfig, book: Book):
        self.config = config
        self.book = book
        self.output_dir = config.resolve_path(config.output)

    def ensure_output_dir(self):
        os.makedirs(self.output_dir, exist_ok=True)

    def output_path(self, suffix: str = '') -> str:
        """Get the output file path."""
        name = self.config.title.replace(' ', '_').replace(':', '')
        if suffix:
            name = f"{name}_{suffix}"
        return os.path.join(self.output_dir, f"{name}.{self.file_extension}")

    def build(self) -> str:
        """Build the output format. Returns the output file path."""
        raise NotImplementedError

    def check_pandoc(self):
        """Verify Pandoc is installed."""
        if not shutil.which('pandoc'):
            raise GeneratorError(
                "Pandoc is not installed. Install it:\n"
                "  macOS:   brew install pandoc\n"
                "  Ubuntu:  apt install pandoc\n"
                "  Windows: choco install pandoc"
            )

    def check_xelatex(self):
        """Verify XeLaTeX is installed."""
        if not shutil.which('xelatex'):
            raise GeneratorError(
                "XeLaTeX is not installed. Install it:\n"
                "  macOS:   brew install --cask mactex-no-gui\n"
                "  Ubuntu:  apt install texlive-xetex texlive-fonts-recommended\n"
                "  Windows: Install MiKTeX from https://miktex.org"
            )

    def assemble_manuscript(self) -> str:
        """Assemble all chapters into a single markdown string with page breaks."""
        parts = []

        for i, chapter in enumerate(self.book.chapters):
            if i > 0:
                parts.append('\n\n\\newpage\n\n')
            parts.append(chapter.content)

        return '\n'.join(parts)

    def run_pandoc(self, args: list, input_file: str, verbose: bool = False) -> str:
        """Run Pandoc with the given arguments. Returns stdout."""
        cmd = ['pandoc'] + args + [input_file]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            raise GeneratorError("Pandoc timed out after 5 minutes")
        except FileNotFoundError:
            self.check_pandoc()
            raise

        if result.returncode != 0:
            # Try to extract a useful error message from LaTeX output
            error = result.stderr
            if verbose:
                console.print(f"[dim]{error}[/dim]")
            # Extract the key error line from LaTeX logs
            for line in error.split('\n'):
                if line.startswith('!') or 'Error' in line:
                    raise GeneratorError(f"Pandoc failed: {line.strip()}")
            raise GeneratorError(f"Pandoc failed with exit code {result.returncode}")

        return result.stdout

    def write_temp_manuscript(self, content: str) -> str:
        """Write manuscript content to a temp file, returning the path."""
        fd, path = tempfile.mkstemp(suffix='.md', prefix='book_formatter_')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def get_lua_filter_path(self, name: str) -> str:
        """Get the path to a bundled Lua filter."""
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'lua_filters',
            name,
        )