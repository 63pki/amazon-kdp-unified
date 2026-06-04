"""Book Formatter CLI — One command to format your book for every platform."""

import os
import sys
import time

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from book_formatter import __version__
from book_formatter.config import load_config, generate_example_config, TRIM_SIZES
from book_formatter.parsers.markdown import parse_manuscript

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name='book-formatter')
def main():
    """Book Formatter — One command to format your book for every platform.

    Free, open-source book formatting for indie authors.
    Replaces Vellum ($250) and Atticus ($150).
    """
    pass


@main.command()
@click.option('--title', prompt='Book title', help='Book title')
@click.option('--author', prompt='Author name', help='Author name')
@click.option('--style', type=click.Choice(['default', 'thriller', 'literary', 'romance']),
              default='default', help='Template style')
def init(title, author, style):
    """Create a book.yaml config file in the current directory."""
    config_path = os.path.join(os.getcwd(), 'book.yaml')

    if os.path.exists(config_path):
        if not click.confirm('book.yaml already exists. Overwrite?'):
            console.print('[yellow]Cancelled.[/yellow]')
            return

    content = generate_example_config(title=title, author=author, style=style)
    with open(config_path, 'w') as f:
        f.write(content)

    console.print(Panel(
        f"[green]Created book.yaml[/green]\n\n"
        f"  Title:  {title}\n"
        f"  Author: {author}\n"
        f"  Style:  {style}\n\n"
        f"Next steps:\n"
        f"  1. Edit book.yaml (set manuscript path, cover, etc.)\n"
        f"  2. Run [bold]book-formatter build[/bold] to generate all formats",
        title="Book Formatter",
        border_style="green",
    ))


@main.command()
@click.option('--format', 'fmt', type=click.Choice(['all', 'epub', 'paperback', 'large-print', 'hardcover']),
              default='all', help='Output format to build')
@click.option('--trim', type=click.Choice(list(TRIM_SIZES.keys())),
              default=None, help='Override trim size for print formats')
@click.option('--config', 'config_path', default='book.yaml', help='Path to book.yaml')
@click.option('--output', default=None, help='Override output directory')
@click.option('--clean', is_flag=True, help='Remove output directory before building')
@click.option('--verbose', is_flag=True, help='Show Pandoc/LaTeX output')
def build(fmt, trim, config_path, output, clean, verbose):
    """Build publication-ready formats from your manuscript."""
    try:
        config = load_config(config_path)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("Run [bold]book-formatter init[/bold] to create a config file.")
        sys.exit(1)

    if output:
        config.output = output
    if trim:
        config.print_settings.trim = trim
    if clean:
        output_dir = config.resolve_path(config.output)
        if os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)

    # Parse manuscript
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing manuscript...", total=None)
        try:
            book = parse_manuscript(config)
        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        progress.update(task, completed=True)

    # Show manuscript summary
    console.print(Panel(
        f"  Chapters:  {len(book.chapters)}\n"
        f"  Words:     {book.word_count:,}\n"
        f"  Est pages: ~{book.estimated_pages}",
        title=f"[bold]{config.title}[/bold] by {config.author}",
        border_style="blue",
    ))

    # Determine what to build
    formats_to_build = []
    if fmt in ('all', 'paperback'):
        formats_to_build.append(('paperback', _build_paperback))
    if fmt in ('all', 'epub'):
        formats_to_build.append(('epub', _build_epub))
    if fmt in ('all', 'large-print'):
        formats_to_build.append(('large-print', _build_large_print))
    if fmt in ('all', 'hardcover'):
        formats_to_build.append(('hardcover', _build_hardcover))

    # Build each format
    results = []
    for name, builder in formats_to_build:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Building {name}...", total=None)
            try:
                start = time.time()
                output_path = builder(config, book, verbose=verbose)
                elapsed = time.time() - start
                size = os.path.getsize(output_path)
                results.append((name, output_path, size, elapsed, None))
            except Exception as e:
                results.append((name, '', 0, 0, str(e)))
            progress.update(task, completed=True)

    # Summary table
    table = Table(title="Build Results", border_style="green")
    table.add_column("Format", style="bold")
    table.add_column("File")
    table.add_column("Size", justify="right")
    table.add_column("Time", justify="right")
    table.add_column("Status")

    for name, path, size, elapsed, error in results:
        if error:
            table.add_row(name, '', '', '', f'[red]FAILED: {error}[/red]')
        else:
            rel_path = os.path.relpath(path)
            size_str = f"{size / 1024:.0f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"
            table.add_row(name, rel_path, size_str, f"{elapsed:.1f}s", '[green]OK[/green]')

    console.print()
    console.print(table)

    # Check for failures
    failures = [r for r in results if r[4] is not None]
    if failures:
        sys.exit(1)


def _build_paperback(config, book, verbose=False):
    from book_formatter.generators.pdf_paperback import PaperbackPDFGenerator
    gen = PaperbackPDFGenerator(config, book)
    return gen.build(verbose=verbose)


def _build_epub(config, book, verbose=False):
    from book_formatter.generators.epub_standard import StandardEPUBGenerator
    gen = StandardEPUBGenerator(config, book)
    return gen.build(verbose=verbose)


def _build_large_print(config, book, verbose=False):
    from book_formatter.generators.pdf_paperback import PaperbackPDFGenerator
    # Reuse paperback generator with large print settings
    config.print_settings.trim = config.print_settings.large_print_trim
    config.typography.body_size = config.typography.large_print_size
    config.typography.line_spacing = 1.5
    gen = PaperbackPDFGenerator(config, book, trim=config.print_settings.large_print_trim)
    return gen.build(verbose=verbose)


def _build_hardcover(config, book, verbose=False):
    from book_formatter.generators.pdf_paperback import PaperbackPDFGenerator
    config.print_settings.trim = config.print_settings.hardcover_trim
    gen = PaperbackPDFGenerator(config, book, trim=config.print_settings.hardcover_trim)
    return gen.build(verbose=verbose)


@main.command()
@click.option('--config', 'config_path', default='book.yaml', help='Path to book.yaml')
def validate(config_path):
    """Check manuscript for common formatting issues."""
    try:
        config = load_config(config_path)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    try:
        book = parse_manuscript(config)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    issues = []

    # Check for empty chapters
    for ch in book.chapters:
        if ch.word_count < 100:
            issues.append(('warning', f'Chapter {ch.number} "{ch.title}" is very short ({ch.word_count} words)'))
        if ch.word_count > 15000:
            issues.append(('info', f'Chapter {ch.number} "{ch.title}" is very long ({ch.word_count:,} words)'))

    # Check for cover image
    if config.cover:
        cover_path = config.resolve_path(config.cover)
        if not os.path.exists(cover_path):
            issues.append(('error', f'Cover image not found: {config.cover}'))
    else:
        issues.append(('info', 'No cover image set (needed for EPUB)'))

    # Check for fonts
    # (basic check - full font validation would need fontconfig)
    if config.typography.body_font == 'EB Garamond':
        issues.append(('info', 'Using EB Garamond — ensure it\'s installed (run: book-formatter fonts check)'))

    # Check trim size
    if config.print_settings.trim not in TRIM_SIZES:
        issues.append(('error', f'Invalid trim size: {config.print_settings.trim}'))

    # Display results
    if not issues:
        console.print(Panel(
            "[green]No issues found![/green]\n\n"
            f"  {len(book.chapters)} chapters, {book.word_count:,} words\n"
            f"  Ready to build.",
            title="Validation",
            border_style="green",
        ))
    else:
        table = Table(title="Validation Results", border_style="yellow")
        table.add_column("Level", style="bold")
        table.add_column("Issue")

        for level, msg in issues:
            color = {'error': 'red', 'warning': 'yellow', 'info': 'blue'}[level]
            table.add_row(f'[{color}]{level}[/{color}]', msg)

        console.print(table)
        console.print(f"\n  {len(book.chapters)} chapters, {book.word_count:,} words")

        errors = [i for i in issues if i[0] == 'error']
        if errors:
            console.print(f"  [red]{len(errors)} error(s) must be fixed before building.[/red]")
            sys.exit(1)


@main.command()
def version():
    """Show version and dependency info."""
    import shutil

    console.print(f"[bold]book-formatter[/bold] v{__version__}")
    console.print()

    deps = [
        ('pandoc', shutil.which('pandoc')),
        ('xelatex', shutil.which('xelatex')),
    ]

    for name, path in deps:
        if path:
            console.print(f"  [green]✓[/green] {name}: {path}")
        else:
            console.print(f"  [red]✗[/red] {name}: not found")


if __name__ == '__main__':
    main()