"""Paperback PDF generator using Pandoc + XeLaTeX."""

import os
import tempfile
from string import Template as StringTemplate

from book_formatter.config import BookConfig
from book_formatter.parsers.ast_model import Book
from book_formatter.generators.base import BaseGenerator


HEADER_TEMPLATE = StringTemplate(r"""\usepackage{fancyhdr}

% Page geometry is set via Pandoc's --variable geometry
% Running headers
\fancypagestyle{bookstyle}{
  \fancyhf{}
  \fancyhead[LE]{\thepage}
  \fancyhead[CE]{\small\textsc{$header_left}}
  \fancyhead[CO]{\small\textsc{$header_right}}
  \fancyhead[RO]{\thepage}
  \fancyfoot{}
  \renewcommand{\headrulewidth}{0.4pt}
  \renewcommand{\footrulewidth}{0pt}
}
\pagestyle{bookstyle}

% Chapter opening pages: no headers
\fancypagestyle{plain}{
  \fancyhf{}
  \renewcommand{\headrulewidth}{0pt}
  \renewcommand{\footrulewidth}{0pt}
}

% Remove extra space before chapter headings
\makeatletter
\renewcommand{\@makechapterhead}[1]{%
  \vspace*{-30pt}%
  {\parindent \z@ \raggedright \normalfont
    \huge\bfseries #1\par\nobreak
    \vskip 20\p@
  }}
\renewcommand{\@makeschapterhead}[1]{%
  \vspace*{-30pt}%
  {\parindent \z@ \raggedright
    \huge\bfseries #1\par\nobreak
    \vskip 20\p@
  }}
\makeatother

% Widows and orphans control
\widowpenalty=10000
\clubpenalty=10000

% Paragraph settings
\setlength{\parindent}{1.5em}
\setlength{\parskip}{0pt}
""")

TITLE_TEMPLATE = StringTemplate(r"""\thispagestyle{empty}
\begin{titlepage}
\centering
\vspace*{1cm}
{\Huge\bfseries $title\par}
$subtitle_block
\vspace{2.5cm}
{\LARGE $author\par}
\vfill
$website_block
{\small Copyright \textcopyright{} $year $author\par}
\vspace{0.3cm}
{\small All rights reserved.\par}
\vspace{0.5cm}
{\footnotesize No part of this book may be reproduced in any form or by any electronic or mechanical means, including information storage and retrieval systems, without written permission from the author, except for the use of brief quotations in a book review.\par}
\vspace{0.3cm}
{\footnotesize This is a work of fiction. Names, characters, places, and incidents either are the product of the author's imagination or are used fictitiously. Any resemblance to actual persons, living or dead, events, or locales is entirely coincidental.\par}
\end{titlepage}
\clearpage
""")


def _latex_escape(text: str) -> str:
    """Escape LaTeX special characters in text."""
    if not text:
        return ''
    replacements = [
        ('&', r'\&'),
        ('%', r'\%'),
        ('$', r'\$'),
        ('#', r'\#'),
        ('_', r'\_'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


class PaperbackPDFGenerator(BaseGenerator):
    """Generate a KDP Print / IngramSpark ready paperback interior PDF."""

    format_name = 'paperback'
    file_extension = 'pdf'

    def __init__(self, config: BookConfig, book: Book, trim: str = None):
        super().__init__(config, book)
        self.trim_key = trim or config.print_settings.trim

    def build(self, verbose: bool = False) -> str:
        self.check_pandoc()
        self.check_xelatex()
        self.ensure_output_dir()

        trim = self.config.get_trim('paperback')
        width, height, gutter, outside, top, bottom = trim

        # Adjust gutter for page count (KDP requirement)
        estimated_pages = self.book.estimated_pages
        if estimated_pages > 150:
            gutter += 0.0625  # Add 1/16" for thicker books
        if estimated_pages > 400:
            gutter += 0.0625

        # Write LaTeX header
        header_content = HEADER_TEMPLATE.substitute(
            header_left=_latex_escape(self.config.get_header_left()),
            header_right=_latex_escape(self.config.get_header_right()),
        )
        header_file = self._write_temp(header_content, suffix='.tex')

        # Write title page
        subtitle = self.config.subtitle
        subtitle_block = ''
        if subtitle:
            subtitle_block = (
                r'\vspace{0.8cm}' '\n'
                r'{\Large ' + _latex_escape(subtitle) + r'\par}'
            )

        website_block = ''
        if self.config.website:
            website_block = (
                r'{\normalsize ' + self.config.website + r'\par}' '\n'
                r'\vspace{0.5cm}'
            )

        title_content = TITLE_TEMPLATE.substitute(
            title=_latex_escape(self.config.title),
            subtitle_block=subtitle_block,
            author=_latex_escape(self.config.author),
            website_block=website_block,
            year=self.config.year,
        )
        title_file = self._write_temp(title_content, suffix='.tex')

        # Assemble manuscript
        manuscript = self.assemble_manuscript()
        manuscript_file = self.write_temp_manuscript(manuscript)

        # Build output path
        output_file = self.output_path(f'paperback_{self.trim_key}')

        # Pandoc arguments
        geometry = (
            f"paperwidth={width}in,"
            f"paperheight={height}in,"
            f"inner={gutter}in,"
            f"outer={outside}in,"
            f"top={top}in,"
            f"bottom={bottom}in,"
            f"twoside"
        )

        args = [
            '--to', 'pdf',
            '--pdf-engine=xelatex',
            '--top-level-division=chapter',
            '--include-in-header', header_file,
            '--include-before-body', title_file,
            '--lua-filter', self.get_lua_filter_path('pagebreak.lua'),
            '--variable', f'geometry:{geometry}',
            '--variable', f'mainfont:{self.config.typography.body_font}',
            '--variable', f'fontsize:{self.config.typography.body_size}',
            '--variable', f'linestretch:{self.config.typography.line_spacing}',
            '--variable', 'documentclass:book',
            '--output', output_file,
        ]

        self.run_pandoc(args, manuscript_file, verbose=verbose)

        # Clean up temp files
        for f in (header_file, title_file, manuscript_file):
            try:
                os.unlink(f)
            except OSError:
                pass

        return output_file

    def _write_temp(self, content: str, suffix: str = '.tex') -> str:
        fd, path = tempfile.mkstemp(suffix=suffix, prefix='book_formatter_')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        return path