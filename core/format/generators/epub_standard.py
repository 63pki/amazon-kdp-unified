"""Standard EPUB 3 generator using Pandoc."""

import os
import tempfile

from book_formatter.config import BookConfig
from book_formatter.parsers.ast_model import Book
from book_formatter.generators.base import BaseGenerator


class StandardEPUBGenerator(BaseGenerator):
    """Generate a standard EPUB 3 for D2D, Google Play, B&N, libraries."""

    format_name = 'epub'
    file_extension = 'epub'

    def build(self, verbose: bool = False) -> str:
        self.check_pandoc()
        self.ensure_output_dir()

        # Assemble manuscript
        manuscript = self.assemble_manuscript()
        manuscript_file = self.write_temp_manuscript(manuscript)

        output_file = self.output_path('ebook')

        # Get CSS path
        css_path = self._get_css_path()

        args = [
            '--to', 'epub3',
            '--epub-chapter-level=1',
            '--toc',
            '--toc-depth=1',
            '--metadata', f'title={self.config.title}',
            '--metadata', f'author={self.config.author}',
            '--lua-filter', self.get_lua_filter_path('pagebreak.lua'),
        ]

        if self.config.subtitle:
            args += ['--metadata', f'subtitle={self.config.subtitle}']

        if css_path and os.path.exists(css_path):
            args += ['--css', css_path]

        # Embed cover image
        cover_path = self._resolve_cover()
        if cover_path:
            args += ['--epub-cover-image', cover_path]

        args += ['--output', output_file]

        self.run_pandoc(args, manuscript_file, verbose=verbose)

        # Clean up
        try:
            os.unlink(manuscript_file)
        except OSError:
            pass

        return output_file

    def _resolve_cover(self) -> str:
        """Resolve cover image path."""
        if not self.config.cover:
            return ''
        path = self.config.resolve_path(self.config.cover)
        if os.path.exists(path):
            return path
        return ''

    def _get_css_path(self) -> str:
        """Get the EPUB CSS path for the current style."""
        # Check for style-specific CSS
        templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'templates',
        )
        style_css = os.path.join(templates_dir, self.config.style, 'epub.css')
        if os.path.exists(style_css):
            return style_css
        # Fall back to default
        default_css = os.path.join(templates_dir, 'default', 'epub.css')
        if os.path.exists(default_css):
            return default_css
        return ''