# © 2026 Sabino Gervasio · os.getenv("GMAIL_USER", "your@email.com") · ${GUMROAD_USERNAME}.gumroad.com
# Data: 2026-04-26 | Progetto: radiOOracle / SportsOracle_Ultra
# Tutti i diritti riservati — All rights reserved.
"""
kdp_publish.py — Modulo autonomo di pubblicazione Amazon KDP
=============================================================
Uso:
    python kdp_publish.py --config libro.json [--draft] [--paperback]

Config JSON minima:
{
    "title": "Titolo del libro",
    "subtitle": "Sottotitolo",                    # opzionale
    "author_first": "Sabino",
    "author_last": "Gervasio",
    "abstract": "Descrizione fino a 4000 char",
    "keywords": ["kw1","kw2","kw3","kw4","kw5","kw6","kw7"],
    "category1": "BISAC category string",          # es. "COMPUTERS / Artificial Intelligence"
    "category2": "BISAC category string",          # opzionale
    "adult_content": true,
    "ai_usage": "no",                              # "no" | "text" | "images" | "translation"
    "ebook_pdf": "path/to/ebook.pdf",
    "price_ebook": 9.99,
    "currency": "USD",                             # "USD" o "EUR"
    "paperback_pdf": "path/to/paperback.pdf",      # opzionale
    "price_paperback": 14.99                       # opzionale
}
"""
import os
import sys, asyncio, json, argparse, sqlite3, re
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

# ─── Paths ────────────────────────────────────────────────────────────────────
COOKIES_FILE  = Path(os.getenv("ORACLE_DIR", str(Path.home() / "SportsOracle_Ultra"))) / "variables" / "amazon_kdp_cookies.json"
KDP_DB        = Path(os.getenv("ORACLE_DIR", str(Path.home() / "SportsOracle_Ultra"))) / "variables" / "kdp_knowledge.db"
KDP_CREATE_IT = "https://kdp.amazon.com/it_IT/title-setup/kindle/new/details"
KDP_CREATE_EN = "https://kdp.amazon.com/en_US/title-setup/kindle/new/details"
BOOKSHELF_IT  = "https://kdp.amazon.com/it_IT/bookshelf"


# ─── Knowledge DB (apprendimento locale) ─────────────────────────────────────

def init_db():
    """Inizializza SQLite knowledge base."""
    con = sqlite3.connect(KDP_DB)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS publications (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        date        TEXT,
        title       TEXT,
        author      TEXT,
        asin        TEXT,
        price       REAL,
        currency    TEXT,
        page_count  INTEGER,
        category1   TEXT,
        category2   TEXT,
        keywords    TEXT,   -- JSON array
        ai_usage    TEXT,
        status      TEXT,   -- 'published' | 'draft' | 'failed'
        royalty_pct REAL
    );
    CREATE TABLE IF NOT EXISTS keywords_freq (
        keyword TEXT PRIMARY KEY,
        count   INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS categories_freq (
        category TEXT PRIMARY KEY,
        count    INTEGER DEFAULT 1
    );
    """)
    con.commit()
    return con


def save_publication(con, config, asin=None, status='published', royalty_pct=None):
    kw = json.dumps(config.get('keywords', []), ensure_ascii=False)
    con.execute("""
        INSERT INTO publications
        (date, title, author, asin, price, currency, category1, category2,
         keywords, ai_usage, status, royalty_pct)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        datetime.now().isoformat(),
        config.get('title', ''),
        f"{config.get('author_first','')} {config.get('author_last','')}",
        asin or '',
        config.get('price_ebook', 0),
        config.get('currency', 'USD'),
        config.get('category1', ''),
        config.get('category2', ''),
        kw,
        config.get('ai_usage', 'no'),
        status,
        royalty_pct,
    ))
    for kw_item in config.get('keywords', []):
        con.execute("""
            INSERT INTO keywords_freq (keyword, count) VALUES (?,1)
            ON CONFLICT(keyword) DO UPDATE SET count = count + 1
        """, (kw_item.lower(),))
    for cat in [config.get('category1',''), config.get('category2','')]:
        if cat:
            con.execute("""
                INSERT INTO categories_freq (category, count) VALUES (?,1)
                ON CONFLICT(category) DO UPDATE SET count = count + 1
            """, (cat,))
    con.commit()


def suggest_from_history(con, topic_words):
    """Suggerisce keyword e categorie basandosi su uso storico."""
    top_kw = con.execute(
        "SELECT keyword, count FROM keywords_freq ORDER BY count DESC LIMIT 20"
    ).fetchall()
    top_cat = con.execute(
        "SELECT category, count FROM categories_freq ORDER BY count DESC LIMIT 10"
    ).fetchall()
    print("\n  📊 Storico KDP — keyword più usate:")
    for kw, c in top_kw[:10]:
        print(f"    {c:3}× {kw}")
    print("\n  📊 Categorie più usate:")
    for cat, c in top_cat[:5]:
        print(f"    {c:3}× {cat}")


# ─── Playwright: wizard KDP ───────────────────────────────────────────────────

async def fill_tab1_details(page, config):
    """Tab 1 — Dettagli libro: titolo, autore, abstract, keywords, categorie."""
    print("\n  📝 Tab 1: Dettagli libro")

    # Titolo
    await page.fill('[id*="book-title"], [name*="title"], input[data-field="title"]',
                    config['title'], timeout=5000)

    # Sottotitolo
    if config.get('subtitle'):
        try:
            await page.fill('[id*="subtitle"], [name*="subtitle"]',
                            config['subtitle'], timeout=3000)
        except: pass

    # Autore
    try:
        await page.fill('[id*="first-name"], [name*="first"]',
                        config.get('author_first', 'Sabino'), timeout=3000)
        await page.fill('[id*="last-name"], [name*="last"]',
                        config.get('author_last', 'Gervasio'), timeout=3000)
    except:
        # Alcuni wizard hanno un campo unico
        try:
            await page.fill('[id*="author"], [name*="author"]',
                            f"{config.get('author_first','')} {config.get('author_last','')}",
                            timeout=3000)
        except: pass

    await page.wait_for_timeout(500)

    # Abstract (max 4000 char)
    abstract = config.get('abstract', '')[:4000]
    try:
        await page.fill('textarea[id*="description"], textarea[name*="description"]',
                        abstract, timeout=5000)
    except:
        try:
            await page.fill('textarea', abstract, timeout=3000)
        except: pass

    await page.wait_for_timeout(500)

    # Contenuto adulti
    if config.get('adult_content', True):
        try:
            await page.click('[id*="adult"] input[type="radio"][value="true"],'
                             ' [id*="mature"] input[value="true"]', timeout=3000)
        except:
            try:
                await page.click("text=Sì, il contenuto è appropriato solo per lettori adulti",
                                  timeout=2000)
            except: pass

    # Utilizzo IA
    ai = config.get('ai_usage', 'no')
    try:
        if ai == 'no':
            await page.click('[value="NO_AI_USED"], [value="no_ai"]', timeout=3000)
        else:
            await page.click('[value="AI_ASSISTED"], [value="ai_used"]', timeout=3000)
    except: pass

    await page.wait_for_timeout(500)

    # Keywords (7 campi separati)
    keywords = config.get('keywords', [])[:7]
    for i, kw in enumerate(keywords):
        try:
            await page.fill(f'input[id*="keyword"][id*="{i}"], '
                             f'input[name*="keyword"][name*="{i}"], '
                             f'input[placeholder*="keyword"]:nth-of-type({i+1})',
                            kw, timeout=2000)
        except:
            try:
                kw_inputs = await page.query_selector_all('input[id*="keyword"]')
                if i < len(kw_inputs):
                    await kw_inputs[i].fill(kw)
            except: pass

    await page.wait_for_timeout(500)

    print(f"    ✅ Titolo: {config['title'][:50]}")
    print(f"    ✅ Autore: {config.get('author_first','')} {config.get('author_last','')}")
    print(f"    ✅ Abstract: {len(abstract)} char")
    print(f"    ✅ Keywords: {', '.join(keywords)}")


async def fill_tab2_categories(page, config):
    """Tab 2 — Categorie (click su 'Avanti' poi seleziona)."""
    print("\n  📂 Tab 2: Categorie")

    cat1 = config.get('category1', '')
    cat2 = config.get('category2', '')

    if cat1:
        try:
            # Apri il selettore categorie
            await page.click('[id*="category"], button:has-text("Aggiungi categoria")', timeout=5000)
            await page.wait_for_timeout(1000)
            # Cerca nella barra di ricerca categorie
            await page.fill('input[placeholder*="category"], input[placeholder*="categoria"]',
                            cat1, timeout=3000)
            await page.wait_for_timeout(1000)
            # Seleziona primo risultato
            await page.click('.category-result:first-child, [class*="category-item"]:first-child',
                             timeout=3000)
            print(f"    ✅ Categoria 1: {cat1[:60]}")
        except Exception as e:
            print(f"    ⚠️ Categoria 1 manuale: {cat1[:40]}")

    await page.wait_for_timeout(500)


async def upload_file(page, file_path, field_selector, label="file"):
    """Carica un file nel campo indicato."""
    path = Path(file_path)
    if not path.exists():
        print(f"    ⚠️ File non trovato: {file_path}")
        return False
    try:
        async with page.expect_file_chooser() as fc_info:
            await page.click(field_selector, timeout=5000)
        fc = await fc_info.value
        await fc.set_files(str(path))
        await page.wait_for_timeout(3000)
        print(f"    ✅ {label} caricato: {path.name}")
        return True
    except Exception as e:
        print(f"    ⚠️ Upload {label} fallito: {e}")
        # Fallback: try direct input[type=file]
        try:
            file_input = await page.query_selector('input[type="file"]')
            if file_input:
                await file_input.set_input_files(str(path))
                await page.wait_for_timeout(3000)
                print(f"    ✅ {label} via input[type=file]")
                return True
        except: pass
        return False


async def fill_tab3_content(page, config):
    """Tab 3 — Carica manoscritto e copertina."""
    print("\n  📄 Tab 3: Contenuto (upload)")

    ebook_pdf = config.get('ebook_pdf', '')
    if ebook_pdf:
        await upload_file(page,
                          ebook_pdf,
                          'button[id*="manuscript"], button:has-text("Carica")',
                          label="Manoscritto eBook")

    cover = config.get('cover_image', '')
    if cover:
        await upload_file(page,
                          cover,
                          'button[id*="cover"], label[for*="cover"]',
                          label="Copertina")

    # Aspetta preview
    print("    ⏳ Attendere anteprima...")
    await page.wait_for_timeout(8000)


async def fill_tab4_pricing(page, config):
    """Tab 4 — Diritti e prezzi."""
    print("\n  💰 Tab 4: Prezzi e royalty")

    price = config.get('price_ebook', 9.99)
    currency = config.get('currency', 'USD')

    # Territorio: tutto il mondo
    try:
        await page.click('[value="WORLD"], [id*="worldwide"]', timeout=3000)
        print("    ✅ Territorio: worldwide")
    except: pass

    # Piano royalty: 70% se prezzo lo consente (2.99-9.99 USD)
    if 2.99 <= price <= 9.99:
        try:
            await page.click('[value="70"], [id*="70percent"], label:has-text("70%")', timeout=3000)
            print("    ✅ Royalty: 70%")
        except: pass

    # Prezzo principale (US o IT)
    market_map = {'USD': 'us', 'EUR': 'it'}
    market = market_map.get(currency, 'us')
    try:
        await page.fill(f'input[id*="price"][id*="{market}"], input[id*="{market}"][id*="price"]',
                        str(price), timeout=3000)
        print(f"    ✅ Prezzo ({market.upper()}): {price} {currency}")
    except:
        try:
            price_inputs = await page.query_selector_all('input[type="number"], input[id*="price"]')
            if price_inputs:
                await price_inputs[0].fill(str(price))
                print(f"    ✅ Prezzo fallback: {price}")
        except: pass

    await page.wait_for_timeout(1000)

    # Leggi royalty calcolata
    try:
        royalty_el = await page.query_selector('[id*="royalty"], [class*="royalty"]')
        if royalty_el:
            royalty_text = await royalty_el.inner_text()
            print(f"    💵 Royalty calcolata: {royalty_text.strip()[:60]}")
    except: pass

    return price


async def check_errors(page):
    """Verifica se ci sono errori di validazione Amazon."""
    errors = []
    try:
        error_els = await page.query_selector_all(
            '[class*="error"], [id*="error"], .a-alert-error, [class*="alert-error"]'
        )
        for el in error_els:
            txt = (await el.inner_text()).strip()
            if txt and len(txt) > 3:
                errors.append(txt[:100])
    except: pass
    return errors


async def save_and_next(page, draft=False):
    """Clicca 'Salva e continua' oppure 'Pubblica' se non draft."""
    btn_labels_save = [
        "Salva e continua", "Save and continue",
        "Continua", "Continue",
        "Avanti", "Next",
    ]
    btn_labels_pub = [
        "Pubblica il libro Kindle", "Publish your Kindle eBook",
        "Pubblica", "Publish",
    ]
    labels = btn_labels_save if draft else btn_labels_pub

    for label in btn_labels_save:
        try:
            btn = page.locator(f"button:has-text('{label}'), input[value='{label}']").first
            if await btn.count() > 0:
                await btn.click()
                await page.wait_for_timeout(2000)
                print(f"    ✅ Click: {label}")
                return True
        except: pass

    if not draft:
        for label in btn_labels_pub:
            try:
                btn = page.locator(f"button:has-text('{label}'), input[value='{label}']").first
                if await btn.count() > 0:
                    await btn.click()
                    await page.wait_for_timeout(3000)
                    print(f"    ✅ Click: {label}")
                    return True
            except: pass

    print("    ⚠️ Bottone non trovato — usa manualmente")
    return False


# ─── Main workflow ────────────────────────────────────────────────────────────

async def publish_ebook(config: dict, draft: bool = True):
    """Pubblica un eBook Kindle su KDP."""
    from playwright.async_api import async_playwright

    print(f"\n  {'[DRAFT]' if draft else '[PUBLISH]'} {config['title'][:60]}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        )
        if COOKIES_FILE.exists():
            await ctx.add_cookies(json.loads(COOKIES_FILE.read_text()))

        page = await ctx.new_page()
        await page.goto(KDP_CREATE_IT, timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        if 'signin' in page.url.lower():
            print("  ⚠️ Non autenticato — naviga manualmente al bookshelf e ricattura i cookie")
            await browser.close()
            return None

        print(f"  URL wizard: {page.url}")

        # ── Tab 1 ───────────────────────────────────────────────────────────
        await fill_tab1_details(page, config)
        await save_and_next(page, draft=True)  # Salva e continua → Tab 2
        await page.wait_for_timeout(2000)

        # ── Tab 2 (categorie, già compilate al tab 1 in alcuni wizard) ─────
        await fill_tab2_categories(page, config)
        await save_and_next(page, draft=True)
        await page.wait_for_timeout(2000)

        # ── Tab 3 (upload) ──────────────────────────────────────────────────
        await fill_tab3_content(page, config)

        # Controlla errori prima di andare avanti
        errs = await check_errors(page)
        if errs:
            print(f"\n  ⚠️ Errori trovati:")
            for e in errs:
                print(f"    • {e}")
            print("  ⚠️ Correggere prima di continuare")
        else:
            await save_and_next(page, draft=True)
            await page.wait_for_timeout(2000)

        # ── Tab 4 (prezzi) ─────────────────────────────────────────────────
        price = await fill_tab4_pricing(page, config)

        # Errori finali
        errs = await check_errors(page)
        if errs:
            print(f"\n  ⚠️ Errori prezzo:")
            for e in errs:
                print(f"    • {e}")
        else:
            print("\n  ✅ Nessun errore trovato")
            if not draft:
                await save_and_next(page, draft=False)  # PUBBLICA
                print("  🚀 Richiesta di pubblicazione inviata!")
            else:
                print("  📝 Salvato come bozza (--draft attivo)")

        # Salva cookie aggiornati
        COOKIES_FILE.write_text(json.dumps(await ctx.cookies(), indent=2))

        # Leggi ASIN se disponibile
        asin = None
        try:
            url_final = page.url
            m = re.search(r'/title-setup/kindle/([A-Z0-9]{10})/', url_final)
            if m:
                asin = m.group(1)
                print(f"  📚 ASIN: {asin}")
        except: pass

        input("\n  ⏸️ Premi INVIO per chiudere il browser...")
        await browser.close()
        return asin


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="KDP AutoPublish — pubblica un libro su Amazon KDP"
    )
    parser.add_argument('--config', '-c', required=True,
                        help="Path al file JSON di configurazione libro")
    parser.add_argument('--draft', '-d', action='store_true', default=True,
                        help="Salva come bozza (default). Usa --no-draft per pubblicare")
    parser.add_argument('--no-draft', dest='draft', action='store_false',
                        help="Pubblica immediatamente (senza --draft)")
    parser.add_argument('--history', action='store_true',
                        help="Mostra storico pubblicazioni e suggerimenti")
    args = parser.parse_args()

    # Inizializza DB
    con = init_db()

    if args.history:
        suggest_from_history(con, [])
        recent = con.execute(
            "SELECT date, title, asin, price, currency, status FROM publications "
            "ORDER BY date DESC LIMIT 10"
        ).fetchall()
        print(f"\n  📚 Ultime {len(recent)} pubblicazioni:")
        for row in recent:
            print(f"    {row[0][:10]} | {row[4]} {row[3]:6} | {row[5]:10} | {row[1][:45]}")
        con.close()
        return

    # Carica config libro
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"  ❌ Config non trovata: {config_path}")
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding='utf-8'))
    print("=" * 65)
    print(f"  KDP AutoPublish — {'BOZZA' if args.draft else 'PUBBLICA'}")
    print("=" * 65)
    print(f"  Libro: {config.get('title','?')[:60]}")
    print(f"  Prezzo: {config.get('price_ebook','?')} {config.get('currency','USD')}")
    print(f"  Keywords: {', '.join(config.get('keywords',[])[:3])}...")

    # Pubblica
    asin = asyncio.run(publish_ebook(config, draft=args.draft))

    # Salva in knowledge DB
    status = 'draft' if args.draft else 'published'
    save_publication(con, config, asin=asin, status=status)
    con.close()

    print(f"\n  ✅ Completato — ASIN: {asin or 'N/A'} — Status: {status}")


if __name__ == "__main__":
    main()