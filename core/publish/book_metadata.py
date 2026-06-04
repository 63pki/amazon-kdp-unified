#!/usr/bin/env python3
# © 2026 Sabino Gervasio · os.getenv("GMAIL_USER", "your@email.com") · ${GUMROAD_USERNAME}.gumroad.com
# Data: 2026-05-02 | Progetto: radiOOracle / SportsOracle_Ultra
# Tutti i diritti riservati — All rights reserved.
"""
Metadata wizard/validator per Amazon KDP.
Legge JSON da book_generator, valida TUTTI i campi, produce checklist.
"""
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")

import json
import re
from pathlib import Path

BISAC_VALID = [
    "COMPUTERS / Artificial Intelligence / General",
    "COMPUTERS / Programming / General",
    "COMPUTERS / Data Science / General",
    "EDUCATION / Teaching Methods & Materials / General",
    "LAW / Administrative Law & Regulatory Practice",
    "MATHEMATICS / General",
    "SCIENCE / General",
    "LANGUAGE ARTS & DISCIPLINES / Study & Teaching",
    "BUSINESS & ECONOMICS / General",
    "SPORTS & RECREATION / General",
    "SELF-HELP / General",
    "HEALTH & FITNESS / General",
    "PHILOSOPHY / General",
    "HISTORY / General",
    "MUSIC / General",
]

PRICE_RANGES = {
    "70pct": (2.99, 9.99),
    "35pct": (0.99, 200.0),
}


def validate_metadata(meta: dict) -> dict:
    errors = []
    warnings = []
    ok = []

    title = meta.get("title", "")
    subtitle = meta.get("subtitle", "")
    description = meta.get("description_html", "") or meta.get("description", "")
    keywords = meta.get("keywords", [])
    bisac = meta.get("bisac", "")
    lang = meta.get("lang", "")
    ai_usage = meta.get("ai_usage", "")
    adult = meta.get("adult_content", None)
    price = meta.get("price_ebook", 0)
    author = meta.get("author", "")

    # Title
    if not title:
        errors.append("TITOLO mancante")
    elif len(title) > 200:
        errors.append(f"TITOLO troppo lungo ({len(title)} > 200 char)")
    elif title == title.upper():
        warnings.append("TITOLO in ALL CAPS — Amazon può bloccare")
    else:
        ok.append(f"Titolo OK ({len(title)} char)")

    # Description
    desc_clean = re.sub(r"<[^>]+>", "", description)
    if len(desc_clean) < 100:
        errors.append(f"DESCRIZIONE troppo corta ({len(desc_clean)} char, minimo 100)")
    elif len(desc_clean) < 500:
        warnings.append(f"DESCRIZIONE corta ({len(desc_clean)} char, consigliato 2000+)")
    elif len(description) > 4000:
        errors.append(f"DESCRIZIONE troppo lunga ({len(description)} char, max 4000)")
    else:
        ok.append(f"Descrizione OK ({len(desc_clean)} char)")

    # Keywords
    if len(keywords) < 7:
        errors.append(f"KEYWORDS insufficienti ({len(keywords)}/7 richieste)")
    else:
        for kw in keywords:
            if len(kw) > 50:
                errors.append(f"Keyword troppo lunga: '{kw[:30]}...' (max 50 char)")
            if title.lower() in kw.lower():
                warnings.append(f"Keyword contiene il titolo (evitare): '{kw}'")
        ok.append(f"Keywords OK ({len(keywords)} frasi)")

    # BISAC
    if not bisac:
        errors.append("CATEGORIA BISAC mancante")
    elif "/" not in bisac:
        warnings.append(f"BISAC non sembra un percorso completo: '{bisac}'")
    else:
        ok.append(f"BISAC: {bisac}")

    # Language
    if not lang:
        errors.append("LINGUA mancante")
    elif lang not in ["IT", "EN", "it", "en", "de", "fr", "es", "pt"]:
        warnings.append(f"Codice lingua insolito: '{lang}'")
    else:
        ok.append(f"Lingua: {lang}")

    # AI usage (mandatory from 2024)
    if not ai_usage:
        errors.append("AI_USAGE mancante — OBBLIGATORIO dal 2024 (valori: text/images/translation/no)")
    elif ai_usage not in ["text", "images", "translation", "no"]:
        errors.append(f"AI_USAGE valore non valido: '{ai_usage}'")
    else:
        ok.append(f"AI Usage dichiarato: {ai_usage}")

    # Adult content
    if adult is None:
        errors.append("ADULT_CONTENT non dichiarato (True/False obbligatorio)")
    else:
        ok.append(f"Contenuto adulti: {'Sì (18+)' if adult else 'No'}")

    # Author
    if not author:
        errors.append("AUTORE mancante")
    else:
        ok.append(f"Autore: {author}")

    # Price
    if price < PRICE_RANGES["35pct"][0]:
        errors.append(f"PREZZO troppo basso: ${price} (minimo $0.99)")
    elif PRICE_RANGES["70pct"][0] <= price <= PRICE_RANGES["70pct"][1]:
        ok.append(f"Prezzo ${price} → royalty 70%")
    else:
        warnings.append(f"Prezzo ${price} → royalty solo 35% (70% richiede $2.99-$9.99)")

    return {"errors": errors, "warnings": warnings, "ok": ok, "valid": len(errors) == 0}


def print_validation(result, meta):
    print(f"\n{'='*60}")
    print(f"  VALIDAZIONE KDP: {meta.get('title', '?')[:50]}")
    print(f"{'='*60}")

    if result["ok"]:
        print("\n  OK:")
        for item in result["ok"]:
            print(f"    [OK] {item}")

    if result["warnings"]:
        print("\n  ATTENZIONE:")
        for w in result["warnings"]:
            print(f"    [!!] {w}")

    if result["errors"]:
        print("\n  ERRORI (blocco pubblicazione):")
        for e in result["errors"]:
            print(f"    [XX] {e}")

    status = "PRONTO PER KDP" if result["valid"] else f"BLOCCATO ({len(result['errors'])} errori)"
    print(f"\n  STATO: {status}")
    print(f"{'='*60}\n")
    return result["valid"]


def load_and_validate(meta_json_path):
    path = Path(meta_json_path)
    if not path.exists():
        print(f"File non trovato: {path}")
        return False
    with open(path, encoding="utf-8") as f:
        meta = json.load(f)
    result = validate_metadata(meta)
    return print_validation(result, meta)


def interactive_wizard():
    """Wizard CLI per compilare metadati manualmente."""
    print("\n=== KDP METADATA WIZARD ===\n")
    meta = {}

    meta["title"] = input("Titolo (max 200 char): ").strip()
    meta["subtitle"] = input("Sottotitolo (invio per saltare): ").strip()
    meta["author"] = input("Autore [Dott. Sabino Gervasio]: ").strip() or "Dott. Sabino Gervasio"
    meta["lang"] = input("Lingua [IT/EN]: ").strip().upper() or "IT"

    print("\nDescrizione HTML (incolla su una riga, poi invio):")
    meta["description_html"] = input("> ").strip()

    print("\n7 Keyword (frasi di ricerca, premi invio dopo ognuna):")
    kws = []
    for i in range(7):
        kw = input(f"  Keyword {i+1}: ").strip()
        if kw:
            kws.append(kw)
    meta["keywords"] = kws

    print(f"\nCategorie disponibili:\n" + "\n".join(f"  {i+1}. {b}" for i, b in enumerate(BISAC_VALID[:10])))
    bisac_idx = input("Numero categoria (o digita manualmente): ").strip()
    if bisac_idx.isdigit() and 1 <= int(bisac_idx) <= len(BISAC_VALID):
        meta["bisac"] = BISAC_VALID[int(bisac_idx) - 1]
    else:
        meta["bisac"] = bisac_idx

    meta["price_ebook"] = float(input("Prezzo eBook [4.99]: ").strip() or "4.99")
    meta["ai_usage"] = input("AI Usage [text/images/translation/no]: ").strip() or "text"
    adult = input("Contenuto adulti 18+? [s/N]: ").strip().lower()
    meta["adult_content"] = adult in ("s", "si", "y", "yes")

    result = validate_metadata(meta)
    is_valid = print_validation(result, meta)

    if is_valid:
        out_path = Path("os.getenv("ORACLE_DIR", str(Path.home() / "SportsOracle_Ultra"))/books_output") / f"metadata_{meta['title'][:30].replace(' ','_')}.json"
        out_path.parent.mkdir(exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"  Salvato: {out_path}")

    return meta, is_valid


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Valida/compila metadati KDP")
    p.add_argument("--validate", help="Percorso JSON metadata da validare")
    p.add_argument("--wizard", action="store_true", help="Wizard interattivo")
    args = p.parse_args()

    if args.validate:
        load_and_validate(args.validate)
    elif args.wizard:
        interactive_wizard()
    else:
        p.print_help()