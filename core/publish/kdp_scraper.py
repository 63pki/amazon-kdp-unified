# © 2026 Sabino Gervasio · os.getenv("GMAIL_USER", "your@email.com") · ${GUMROAD_USERNAME}.gumroad.com
# Data: 2026-04-26 | Progetto: radiOOracle / SportsOracle_Ultra
# Tutti i diritti riservati — All rights reserved.
"""
kdp_scraper.py — Scrapa Amazon KDP Bookshelf COMPLETO (tutte le pagine)
=======================================================================
1. Apre browser Playwright (con cookie se già salvati → login automatico)
2. Naviga bookshelf KDP + scorre tutte le pagine
3. Scrapa: titolo, ASIN, stato, tipo, lingua per ogni libro
4. Crea note Obsidian + indice + connessioni
"""
import os
import sys, asyncio, json, re
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

COOKIES_FILE = Path("os.getenv("ORACLE_DIR", str(Path.home() / "SportsOracle_Ultra"))/variables/amazon_kdp_cookies.json")
OBSIDIAN_ROOT = Path("os.getenv("USER_HOME", str(Path.home())) + "/Documents/Obsidian Vault")
KDP_BOOKS_DIR = OBSIDIAN_ROOT / "Amazon KDP"
KDP_BOOKS_DIR.mkdir(parents=True, exist_ok=True)
BOOKSHELF_URL = "https://kdp.amazon.com/en_US/bookshelf"


def stato_it(status_raw: str) -> str:
    s = status_raw.lower()
    if any(x in s for x in ["live", "published", "pubblicato"]):
        return "✅ PUBBLICATO"
    if "draft" in s:
        return "📝 BOZZA"
    if any(x in s for x in ["review", "pending", "in process"]):
        return "🟠 IN REVISIONE"
    if any(x in s for x in ["suppressed", "blocked", "unpublished"]):
        return "🔴 BLOCCATO"
    return f"❓ {status_raw}" if status_raw else "❓ Sconosciuto"


def safe_filename(title: str, asin: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', '', title).strip()[:50]
    return name if name else f"ASIN {asin}"


async def wait_for_login(page):
    """Carica cookie o aspetta login manuale."""
    print("\n  Apro KDP Bookshelf...")
    await page.goto(BOOKSHELF_URL, timeout=30000, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    # Controlla se già loggato
    if "bookshelf" in page.url and "signin" not in page.url:
        print("  ✅ Già loggato!\n")
        return True

    print("  ⚠️  Serve login. Il browser è aperto — effettua login su KDP.")
    print("  Lo script continua automaticamente...\n")
    for i in range(600):
        url = page.url
        if "kdp.amazon.com" in url and not any(x in url for x in ["signin", "ap/sign", "auth"]):
            if "bookshelf" not in url:
                await page.goto(BOOKSHELF_URL, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
            print("  ✅ Login rilevato!\n")
            return True
        if i % 20 == 0 and i > 0:
            print(f"  ⏳ Attesa login... {i}s — URL: {page.url[:70]}")
            sys.stdout.flush()
        await asyncio.sleep(1)
    return False


async def extract_books_from_page(page) -> list[dict]:
    """Estrae tutti i libri dalla pagina corrente."""
    await page.wait_for_timeout(2000)
    books = []

    # Prova selettori KDP (2024/2025)
    # KDP usa righe <tr> con id="book-container-ASIN"
    rows = await page.query_selector_all("tr[id*='book-container']")

    if not rows:
        # Fallback: cercare le righe della tabella bookshelf
        rows = await page.query_selector_all("tr.format-row, tr[class*='title-row'], tbody > tr")

    print(f"    → Trovate {len(rows)} righe")

    for row in rows:
        try:
            book = {"asin": "", "title": "", "status": "", "type": "", "language": ""}

            # ASIN dall'ID della riga
            row_id = await row.get_attribute("id") or ""
            asin_match = re.search(r'([A-Z0-9]{10})', row_id)
            if asin_match:
                book["asin"] = asin_match.group(1)

            # Titolo
            for sel in [
                "[class*='title-name']",
                ".book-title a",
                "span[class*='title']",
                "a[href*='/title-setup/']",
                "td:first-child a",
                ".title-name",
            ]:
                el = await row.query_selector(sel)
                if el:
                    text = (await el.inner_text()).strip()
                    if text and len(text) > 2:
                        book["title"] = text
                        break

            # Se non trovato il titolo, cerca ASIN nel testo della riga e skippa
            if not book["title"] and not book["asin"]:
                continue

            # Status (Live / Draft / etc.)
            for sel in [
                "[class*='status-badge']",
                "span[class*='status']",
                "td[class*='status']",
                "[data-status]",
                ".status",
            ]:
                el = await row.query_selector(sel)
                if el:
                    book["status"] = (await el.inner_text()).strip()
                    break

            # Tipo (eBook / Paperback / Hardcover)
            for sel in [
                "[class*='format']",
                "td[class*='type']",
                ".format-badge",
            ]:
                el = await row.query_selector(sel)
                if el:
                    book["type"] = (await el.inner_text()).strip()
                    break

            if book["asin"] or book["title"]:
                books.append(book)
        except Exception as e:
            continue

    # Se 0 righe trovate → fallback testo pagina per ASIN
    if not books:
        print("    → Fallback: estrazione ASIN da testo pagina")
        text = await page.inner_text("body")

        # Cerca pattern ASIN (10 caratteri maiuscoli/numeri, inizia con B0 o simili)
        asins = re.findall(r'\b(B0[A-Z0-9]{8})\b', text)
        asins = list(dict.fromkeys(asins))  # dedup preserving order

        # Cerca titoli vicino agli ASIN
        for asin in asins:
            # Cerca nel testo il contesto intorno all'ASIN
            idx = text.find(asin)
            context = text[max(0, idx-200):idx+200]

            # Estrai linee di testo vicine che potrebbero essere titoli
            lines = [l.strip() for l in context.split('\n') if l.strip() and len(l.strip()) > 10]
            title = lines[0] if lines else f"ASIN {asin}"

            books.append({
                "asin": asin,
                "title": title[:80],
                "status": "Unknown",
                "type": "Unknown",
                "language": "Unknown",
            })

    return books


async def get_next_page_url(page) -> str | None:
    """Trova il link alla pagina successiva della bookshelf."""
    # KDP usa pulsante "Next" o link di paginazione
    for sel in [
        "a[class*='next']",
        "a:has-text('Next')",
        "li.next a",
        "[aria-label='Next page']",
        "a[data-action='next']",
    ]:
        el = await page.query_selector(sel)
        if el:
            href = await el.get_attribute("href")
            if href:
                return href if href.startswith("http") else f"https://kdp.amazon.com{href}"
    return None


def create_book_note(book: dict) -> Path:
    """Crea nota Obsidian per un libro."""
    fname = safe_filename(book["title"], book["asin"]) + ".md"
    note_path = KDP_BOOKS_DIR / fname

    stato = stato_it(book["status"])
    tag = "pubblicato" if "PUBBLICATO" in stato else ("bozza" if "BOZZA" in stato else "in-sviluppo")
    asin = book.get("asin", "N/A")
    amazon_url = f"https://www.amazon.it/dp/{asin}" if len(asin) == 10 else ""

    content = f"""---
tags: [amazon-kdp, {tag}]
asin: {asin}
stato: {stato}
tipo: {book.get('type', 'Unknown')}
lingua: {book.get('language', 'Unknown')}
aggiornato: {datetime.now().strftime('%Y-%m-%d')}
---

# {book['title']}

**ASIN**: `{asin}`
**Stato**: {stato}
**Tipo**: {book.get('type', 'Unknown')}
**Lingua**: {book.get('language', 'Unknown')}
{"**Amazon.it**: " + amazon_url if amazon_url else ""}

← [[Amazon KDP]]
← [[radiOOracle]] (promozione radio)
"""
    note_path.write_text(content, encoding="utf-8")
    return note_path


def create_kdp_index(books: list[dict]):
    """Crea/aggiorna nota indice Amazon KDP."""
    index_path = OBSIDIAN_ROOT / "Progetti" / "Amazon KDP.md"

    pubblicati = [b for b in books if "PUBBLICATO" in stato_it(b.get("status", ""))]
    bozze = [b for b in books if "BOZZA" in stato_it(b.get("status", ""))]
    altri = [b for b in books if b not in pubblicati and b not in bozze]

    def link(b):
        name = safe_filename(b["title"], b["asin"])
        asin = b.get("asin", "N/A")
        url = f"https://www.amazon.it/dp/{asin}" if len(asin) == 10 else ""
        return f"- [[{name}]] — ASIN `{asin}`" + (f" — [Amazon]({url})" if url else "")

    content = f"""---
tags: [progetto, amazon-kdp, priorita-alta]
totale-libri: {len(books)}
aggiornato: {datetime.now().strftime('%Y-%m-%d')}
---

# Amazon KDP ⭐ PRIORITÀ ALTA

> Royalty passive — monetizzazione 100% automatica.

**Account**: Sabino Gervasio
**Bookshelf**: https://kdp.amazon.com/en_US/bookshelf
**Totale libri trovati**: {len(books)}

## ✅ PUBBLICATI ({len(pubblicati)})

{chr(10).join(link(b) for b in pubblicati) or '_Nessuno_'}

## 📝 BOZZE ({len(bozze)})

{chr(10).join(link(b) for b in bozze) or '_Nessuno_'}

## ❓ Altri / Stato sconosciuto ({len(altri)})

{chr(10).join(link(b) for b in altri) or '_Nessuno_'}

## Da caricare (pronti in locale)

- [[Oracle Book]] IT → `IL_FATTORE_ORACLE_KDP_v2.docx`
- [[Oracle Book]] EN → `THE_ORACLE_FACTOR_KDP_v2.docx`
- Script: `kdp_opener.py`

## Connessioni

[[Oracle Book]] ← contenuto principale
[[radiOOracle]] ← promuove tutti i libri in radio
[[Gumroad]] ← vendita parallela
[[LinkedIn]] ← promozione thought leadership
"""
    index_path.write_text(content, encoding="utf-8")
    print(f"  📄 Indice KDP aggiornato: {index_path}")


async def main():
    print("=" * 60)
    print("  AMAZON KDP — Full Bookshelf Scraper + Obsidian")
    print("=" * 60)

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized", "--no-sandbox"],
        )
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        )

        # Carica cookie salvati
        if COOKIES_FILE.exists():
            cookies = json.loads(COOKIES_FILE.read_text())
            await ctx.add_cookies(cookies)
            print(f"  🍪 Cookie caricati ({len(cookies)} cookies)")

        page = await ctx.new_page()

        if not await wait_for_login(page):
            print("  ❌ Login fallito. Riprova.")
            await browser.close()
            return

        # Salva cookie aggiornati
        cookies = await ctx.cookies()
        COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
        print(f"  🍪 Cookie salvati: {len(cookies)}")

        # Scrapa tutte le pagine
        all_books = []
        page_num = 1

        while True:
            print(f"\n  📄 Pagina {page_num} — URL: {page.url[:70]}")
            sys.stdout.flush()

            # Screenshot di ogni pagina
            ss_path = Path(f"os.getenv("ORACLE_DIR", str(Path.home() / "SportsOracle_Ultra"))/variables/kdp_page_{page_num}.png")
            await page.screenshot(path=str(ss_path), full_page=True)

            books = await extract_books_from_page(page)
            print(f"  📚 Pagina {page_num}: {len(books)} libri")
            sys.stdout.flush()

            for b in books:
                print(f"    - {b.get('title','?')[:60]} [{b.get('asin','?')}] {stato_it(b.get('status',''))}")
            sys.stdout.flush()

            all_books.extend(books)

            # Prossima pagina?
            next_url = await get_next_page_url(page)
            if next_url:
                print(f"  → Pagina successiva: {next_url[:60]}")
                await page.goto(next_url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                page_num += 1
            else:
                print(f"\n  ✅ Fine bookshelf — {page_num} pagine, {len(all_books)} libri totali")
                break

        # Crea note Obsidian
        print(f"\n  📝 Creo note Obsidian...")
        sys.stdout.flush()
        for book in all_books:
            note = create_book_note(book)
            print(f"  {'✅' if 'PUBBLICATO' in stato_it(book.get('status','')) else '📝'} {book.get('title','?')[:50]} → {note.name}")
            sys.stdout.flush()

        create_kdp_index(all_books)

        # Salva JSON
        json_path = Path("os.getenv("ORACLE_DIR", str(Path.home() / "SportsOracle_Ultra"))/variables/kdp_books.json")
        json_path.write_text(json.dumps(all_books, indent=2, ensure_ascii=False))
        print(f"\n  💾 Dati: {json_path} ({len(all_books)} libri)")
        print("  ✅ Scraping completo! Apri Obsidian per vedere le connessioni.")
        sys.stdout.flush()

        await asyncio.sleep(3)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())