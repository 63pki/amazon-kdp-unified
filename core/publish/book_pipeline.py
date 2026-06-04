#!/usr/bin/env python3
# © 2026 Sabino Gervasio · os.getenv("GMAIL_USER", "your@email.com") · ${GUMROAD_USERNAME}.gumroad.com
# Data: 2026-05-02 | Progetto: radiOOracle / SportsOracle_Ultra
# Tutti i diritti riservati — All rights reserved.
"""
Book Pipeline — Orchestratore completo
Da argomento a DOCX+PDF+Cover+Metadata validati.

Uso: python book_pipeline.py --topic "Machine Learning" [--lang IT] [--length medio]
"""
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")

import argparse
import json
import time
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("os.getenv("ORACLE_DIR", str(Path.home() / "SportsOracle_Ultra"))/books_output")


def banner():
    print("""
╔══════════════════════════════════════════════════════╗
║        BOOK PIPELINE v1.0 — Sabino Gervasio          ║
║  AI Generation + Refinement + Cover + KDP Metadata   ║
╚══════════════════════════════════════════════════════╝""")


def step(n, total, label):
    print(f"\n[{n}/{total}] {label}")
    print("─" * 50)


def run_pipeline(topic, lang="IT", length="medio", target="intermedio",
                 audience="adult", refine=True, learn=True, skip_cover=False):
    banner()
    print(f"\nTopico: {topic}")
    print(f"Lingua: {lang} | Lunghezza: {length} | Livello: {target}")
    print(f"Raffinamento: {'SI (qwen3-coder)' if refine else 'NO'}")
    print(f"Learning cycle: {'SI' if learn else 'NO'}")

    t0 = time.time()
    results = {}
    TOTAL_STEPS = 6 if not skip_cover else 5

    # ── Step 1: Content generation ──────────────────────────────────
    step(1, TOTAL_STEPS, "Generazione contenuto AI (phi4 + refiner)")
    try:
        from book_generator import generate_book
        docx_path, meta = generate_book(
            topic=topic, lang=lang, length=length,
            target=target, audience=audience, refine=refine,
        )
        results["docx"] = docx_path
        results["meta"] = meta
        results["title"] = meta.get("title", topic)
    except Exception as e:
        print(f"  ERRORE generazione: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    # ── Step 2: Metadata validation ──────────────────────────────────
    step(2, TOTAL_STEPS, "Validazione metadati KDP")
    try:
        from book_metadata import validate_metadata, print_validation
        validation = validate_metadata(meta)
        is_valid = print_validation(validation, meta)
        results["metadata_valid"] = is_valid
        if not is_valid:
            print("  ⚠️  Metadati con errori — controlla prima di pubblicare su KDP!")
    except Exception as e:
        print(f"  ERRORE validazione: {e}")

    # ── Step 3: PDF formatting ───────────────────────────────────────
    step(3, TOTAL_STEPS, "Conversione DOCX → PDF KDP")
    try:
        from book_formatter import convert_docx_to_pdf
        pdf_path = convert_docx_to_pdf(docx_path)
        results["pdf"] = pdf_path
    except Exception as e:
        print(f"  ERRORE conversione PDF: {e}")
        results["pdf"] = None

    # ── Step 4: Cover generation ─────────────────────────────────────
    if not skip_cover:
        step(4, TOTAL_STEPS, "Generazione copertine (eBook + Print)")
        try:
            from book_cover_gen import generate_covers
            # Estimate page count from word count (avg 250 words/page for 6x9)
            word_count = meta.get("word_count", 20000)
            est_pages = max(30, word_count // 250)
            covers = generate_covers(
                title=meta.get("title", topic),
                subtitle=meta.get("subtitle", ""),
                page_count=est_pages,
                topic=topic,
            )
            results["covers"] = covers
            # Add cover path to metadata
            meta["cover_ebook"] = covers.get("ebook")
            meta["cover_print"] = covers.get("print")
            meta["estimated_pages"] = est_pages
        except Exception as e:
            print(f"  ERRORE copertina: {e}")
            results["covers"] = {}

    # ── Step 5: Save final metadata ──────────────────────────────────
    step(5 if not skip_cover else 4, TOTAL_STEPS, "Salvataggio metadati finali")
    try:
        meta_path = docx_path.replace(".docx", "_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        results["metadata_json"] = meta_path
        print(f"  Metadati: {meta_path}")
    except Exception as e:
        print(f"  ERRORE salvataggio metadati: {e}")

    # ── Step 6: Learning cycle ───────────────────────────────────────
    if learn:
        step(TOTAL_STEPS, TOTAL_STEPS, "Ciclo apprendimento automatico")
        try:
            from book_learner import run_learning_cycle
            insights = run_learning_cycle(verbose=False)
            n_suggestions = len(insights.get("db_stats", {}).get("suggestions", []))
            print(f"  GitHub tool scansionati: {len(insights.get('github_tools', []))}")
            print(f"  Suggerimenti generati: {n_suggestions}")
        except Exception as e:
            print(f"  ERRORE learning: {e}")

    # ── Summary ──────────────────────────────────────────────────────
    elapsed = round(time.time() - t0)
    mins, secs = divmod(elapsed, 60)

    print(f"\n{'═'*60}")
    print(f"  PIPELINE COMPLETATA in {mins}m {secs}s")
    print(f"{'═'*60}")
    print(f"\n  TITOLO:   {results.get('title', '?')}")
    print(f"  DOCX:     {results.get('docx', 'n/d')}")
    print(f"  PDF:      {results.get('pdf', 'n/d')}")
    if results.get("covers"):
        print(f"  COVER eBook: {results['covers'].get('ebook', 'n/d')}")
        print(f"  COVER Print: {results['covers'].get('print', 'n/d')}")
    print(f"  METADATA: {results.get('metadata_json', 'n/d')}")
    print(f"  KDP READY: {'SI' if results.get('metadata_valid') else 'NO — verifica errori'}")
    print(f"\n  PROSSIMI STEP:")
    print(f"  1. Controlla il DOCX in Word/LibreOffice")
    print(f"  2. Controlla la copertina eBook (min 2560×1600px)")
    print(f"  3. Usa kdp_publish.py per caricare su Amazon KDP")
    print(f"  4. Dopo 90gg: carica su Draft2Digital per altri store")
    print(f"{'═'*60}\n")

    return results


def interactive_mode():
    """Modalità wizard interattivo se nessun argomento passato."""
    print("\n=== BOOK PIPELINE WIZARD ===\n")
    topic = input("Argomento del libro: ").strip()
    if not topic:
        print("Argomento obbligatorio.")
        sys.exit(1)

    lang = input("Lingua [IT/EN, default IT]: ").strip().upper() or "IT"
    length = input("Lunghezza [corto/medio/lungo, default medio]: ").strip() or "medio"
    target = input("Livello [principiante/intermedio/avanzato, default intermedio]: ").strip() or "intermedio"
    adult = input("Solo adulti 18+? [s/N]: ").strip().lower()
    audience = "adult" if adult in ("s", "si", "y") else "all"
    refine = input("Abilita raffinamento qwen3-coder? [S/n]: ").strip().lower()
    refine = refine not in ("n", "no")

    return run_pipeline(topic, lang, length, target, audience, refine)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Pipeline libro completa: AI → KDP")
    p.add_argument("--topic", help="Argomento del libro")
    p.add_argument("--lang", default="IT", choices=["IT", "EN"])
    p.add_argument("--length", default="medio", choices=["corto", "medio", "lungo"])
    p.add_argument("--target", default="intermedio",
                   choices=["principiante", "intermedio", "avanzato"])
    p.add_argument("--audience", default="adult", choices=["adult", "all"])
    p.add_argument("--no-refine", action="store_true", help="Salta raffinamento qwen3-coder")
    p.add_argument("--no-learn", action="store_true", help="Salta ciclo apprendimento")
    p.add_argument("--no-cover", action="store_true", help="Salta generazione copertine")
    args = p.parse_args()

    if not args.topic:
        interactive_mode()
    else:
        run_pipeline(
            topic=args.topic,
            lang=args.lang,
            length=args.length,
            target=args.target,
            audience=args.audience,
            refine=not args.no_refine,
            learn=not args.no_learn,
            skip_cover=args.no_cover,
        )