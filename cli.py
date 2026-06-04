#!/usr/bin/env python3
"""
KDP Unified — Master CLI
========================
One tool for the complete Amazon KDP publishing pipeline.

Merges features from 28 repositories into a single cohesive workflow.

Usage:
    kdp research keywords "cozy mystery"     # Mine keywords (kdp-scout)
    kdp research niche "cozy mystery"        # Score niche opportunity
    kdp research competitors B08XYZ123       # Track competitor by ASIN
    kdp research bsr 45000                   # Estimate daily sales from BSR
    kdp research trending                    # Discover trending niches

    kdp write new                            # Interactive book setup wizard
    kdp write outline "topic"               # Generate book outline
    kdp write draft                          # Draft all chapters (parallel)
    kdp write edit                           # Adversarial self-edit loop
    kdp write evaluate                       # Score chapter quality

    kdp format epub manuscript.md           # Format to EPUB3 (KDP Kindle)
    kdp format pdf manuscript.md            # Format to paperback PDF
    kdp format all manuscript.md            # All formats (epub + pdf + hardcover)
    kdp format normalize book.epub          # Normalize/validate EPUB

    kdp cover generate                       # AI cover generation
    kdp cover pil                            # PIL gradient cover (fast)

    kdp metadata generate                    # Generate KDP metadata JSON

    kdp publish single                       # Playwright single-book publish
    kdp publish bulk books.csv              # CSV bulk publish (auto-kdp)
    kdp publish scrape                       # Sync bookshelf to CSV

    kdp audiobook generate                   # Full audiobook pipeline

    kdp pipeline full "book topic"          # End-to-end: research → write → format → publish
    kdp pipeline agency "book topic"        # 8-agent parallel pipeline (kindle-book-agency)
"""

import argparse
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def cmd_research(args):
    """Research subcommands — powered by kdp-scout."""
    from core.research.cli import main as scout_cli
    # Remap args to kdp-scout CLI format
    sys.argv = ['kdp-scout'] + args.subargs
    scout_cli()


def cmd_write(args):
    """AI writing subcommands."""
    subcmd = args.subargs[0] if args.subargs else 'help'

    if subcmd == 'new':
        from core.content.setup_book import main
        main()

    elif subcmd == 'outline':
        topic = ' '.join(args.subargs[1:]) if len(args.subargs) > 1 else None
        if not topic:
            print("Usage: kdp write outline \"your book topic\"")
            sys.exit(1)
        from core.content.pipeline.build_outline import main
        main(topic)

    elif subcmd == 'draft':
        # Parallel chapter drafting (kindle-book-agency style)
        from core.content.write_chapters import main
        main()

    elif subcmd == 'edit':
        # Adversarial self-edit loop (autonovel style)
        from core.content.pipeline.adversarial_edit import main
        main()

    elif subcmd == 'evaluate':
        from core.content.pipeline.evaluate import main
        main()

    elif subcmd == 'agency':
        # Full 8-agent parallel pipeline
        topic = ' '.join(args.subargs[1:]) if len(args.subargs) > 1 else None
        from core.content.agency_main import main
        main(topic)

    else:
        print(f"Unknown write subcommand: {subcmd}")
        print("Available: new, outline, draft, edit, evaluate, agency")
        sys.exit(1)


def cmd_format(args):
    """Formatting subcommands — powered by rxpelle/book-formatter."""
    from core.format.cli import main as formatter_cli
    sys.argv = ['kdp-format'] + args.subargs
    formatter_cli()


def cmd_cover(args):
    """Cover generation subcommands."""
    subcmd = args.subargs[0] if args.subargs else 'help'

    if subcmd == 'generate':
        # AI cover (autonovel gen_cover)
        from core.cover.gen_cover import main
        main()
    elif subcmd == 'pil':
        # PIL gradient cover (sabbonzo)
        from core.cover.book_cover_gen import generate_cover
        generate_cover()
    else:
        print(f"Unknown cover subcommand: {subcmd}")
        print("Available: generate, pil")
        sys.exit(1)


def cmd_metadata(args):
    """KDP metadata generation — powered by duchangyu."""
    from core.content.generate_kdp_metadata import main
    main()


def cmd_publish(args):
    """Publishing subcommands."""
    subcmd = args.subargs[0] if args.subargs else 'help'

    if subcmd == 'single':
        # Playwright single-book (sabbonzo)
        from core.publish.kdp_publish import main
        main()
    elif subcmd == 'bulk':
        csv_path = args.subargs[1] if len(args.subargs) > 1 else 'data/books.csv'
        print(f"Bulk publishing from {csv_path} via auto-kdp...")
        os.system(f"npx ts-node core/publish/index.ts --csv {csv_path}")
    elif subcmd == 'scrape':
        os.system("npx ts-node core/publish/index.ts scrape")
    else:
        print(f"Unknown publish subcommand: {subcmd}")
        print("Available: single, bulk, scrape")
        sys.exit(1)


def cmd_audiobook(args):
    """Audiobook pipeline — powered by autonovel."""
    subcmd = args.subargs[0] if args.subargs else 'generate'
    if subcmd == 'generate':
        from core.audiobook.gen_audiobook import main
        main()
    else:
        print(f"Unknown audiobook subcommand: {subcmd}")
        sys.exit(1)


def cmd_pipeline(args):
    """Full end-to-end pipeline."""
    subcmd = args.subargs[0] if args.subargs else 'help'
    topic = ' '.join(args.subargs[1:]) if len(args.subargs) > 1 else None

    if subcmd == 'full':
        if not topic:
            print("Usage: kdp pipeline full \"your book topic\"")
            sys.exit(1)
        print(f"\n🚀 Starting full KDP pipeline for: {topic}\n")
        print("Phase 1/5 — Research...")
        os.system(f'python3 -c "from core.research.cli import main; main()" keywords "{topic}"')
        print("\nPhase 2/5 — Writing...")
        os.system(f'python3 core/content/agency_main.py "{topic}"')
        print("\nPhase 3/5 — Formatting...")
        os.system('python3 cli.py format all output/manuscript.md')
        print("\nPhase 4/5 — Cover...")
        os.system('python3 cli.py cover pil')
        print("\nPhase 5/5 — Metadata...")
        os.system('python3 cli.py metadata generate')
        print("\n✅ Pipeline complete! Output in ./output/")

    elif subcmd == 'agency':
        # kindle-book-agency 8-agent DAG
        if not topic:
            print("Usage: kdp pipeline agency \"your book topic\"")
            sys.exit(1)
        from core.content.agency_main import main
        main(topic)
    else:
        print(f"Unknown pipeline subcommand: {subcmd}")
        print("Available: full, agency")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog='kdp',
        description='KDP Unified — Complete Amazon KDP Publishing Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('command', choices=['research', 'write', 'format', 'cover', 'metadata', 'publish', 'audiobook', 'pipeline'],
                        help='Command group')
    parser.add_argument('subargs', nargs=argparse.REMAINDER, help='Subcommand and arguments')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    dispatch = {
        'research': cmd_research,
        'write':    cmd_write,
        'format':   cmd_format,
        'cover':    cmd_cover,
        'metadata': cmd_metadata,
        'publish':  cmd_publish,
        'audiobook':cmd_audiobook,
        'pipeline': cmd_pipeline,
    }
    dispatch[args.command](args)


if __name__ == '__main__':
    main()
