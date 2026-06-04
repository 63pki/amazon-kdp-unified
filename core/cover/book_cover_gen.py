#!/usr/bin/env python3
# © 2026 Sabino Gervasio · os.getenv("GMAIL_USER", "your@email.com") · ${GUMROAD_USERNAME}.gumroad.com
# Data: 2026-05-02 | Progetto: radiOOracle / SportsOracle_Ultra
# Tutti i diritti riservati — All rights reserved.
"""
Cover generator: eBook (2560×1600) + Print con dorso (formula KDP).
Usa Pillow. Output: JPEG eBook + PDF copertina cartaceo.
"""
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installa: pip install Pillow")
    sys.exit(1)

OUTPUT_DIR = Path(os.getenv("ORACLE_DIR", str(Path.home() / "SportsOracle_Ultra"))) / "books_output"

# Palette professionale — 6 temi
THEMES = {
    "tech":    {"bg": "#0d1b2a", "accent": "#00b4d8", "text": "#ffffff", "sub": "#90e0ef"},
    "business":{"bg": "#1a1a2e", "accent": "#e94560", "text": "#ffffff", "sub": "#f4a261"},
    "science": {"bg": "#0f3460", "accent": "#e94560", "text": "#ffffff", "sub": "#a8dadc"},
    "culture": {"bg": "#2d4739", "accent": "#f0c040", "text": "#ffffff", "sub": "#b7e4c7"},
    "sport":   {"bg": "#1b1b2f", "accent": "#ff6b35", "text": "#ffffff", "sub": "#ffd166"},
    "default": {"bg": "#16213e", "accent": "#0f3460", "text": "#ffffff", "sub": "#e94560"},
}

FONT_PATHS = [
    "C:/Windows/Fonts/Arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "C:/Windows/Fonts/verdana.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
]


def load_font(size):
    for fp in FONT_PATHS:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_cover_face(draw, img_w, img_h, title, subtitle, author, theme, is_spine=False):
    """Draw cover on a Draw object for a given region."""
    colors_t = theme
    bg = hex_to_rgb(colors_t["bg"])
    accent = hex_to_rgb(colors_t["accent"])
    txt = hex_to_rgb(colors_t["text"])
    sub = hex_to_rgb(colors_t["sub"])

    # Gradient background
    for y in range(img_h):
        ratio = y / img_h
        r = int(bg[0] * (1 - ratio * 0.3))
        g = int(bg[1] * (1 - ratio * 0.3))
        b = int(bg[2] * (1 - ratio * 0.3))
        draw.line([(0, y), (img_w, y)], fill=(r, g, b))

    # Accent bar top
    draw.rectangle([(0, 0), (img_w, 8)], fill=accent)
    draw.rectangle([(0, img_h - 8), (img_w, img_h)], fill=accent)

    # Decorative diagonal lines
    for i in range(0, img_w, 80):
        draw.line([(i, 0), (i + 60, img_h)], fill=(*accent, 30), width=1)

    # Title
    font_title = load_font(min(int(img_w * 0.08), 72))
    font_sub = load_font(min(int(img_w * 0.045), 40))
    font_auth = load_font(min(int(img_w * 0.04), 32))

    margin = int(img_w * 0.06)
    max_w = img_w - margin * 2
    y_pos = int(img_h * 0.18)

    title_lines = wrap_text(title, font_title, max_w, draw)
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        w = bbox[2] - bbox[0]
        draw.text(((img_w - w) // 2, y_pos), line, font=font_title, fill=txt)
        y_pos += bbox[3] - bbox[1] + 8

    # Accent separator
    draw.rectangle([(margin, y_pos + 10), (img_w - margin, y_pos + 14)], fill=accent)
    y_pos += 30

    # Subtitle
    if subtitle:
        sub_lines = wrap_text(subtitle, font_sub, max_w, draw)
        for line in sub_lines[:3]:
            bbox = draw.textbbox((0, 0), line, font=font_sub)
            w = bbox[2] - bbox[0]
            draw.text(((img_w - w) // 2, y_pos), line, font=font_sub, fill=hex_to_rgb(colors_t["sub"]))
            y_pos += bbox[3] - bbox[1] + 6

    # Author at bottom
    auth_text = f"Dott. Sabino Gervasio"
    bbox = draw.textbbox((0, 0), auth_text, font=font_auth)
    w = bbox[2] - bbox[0]
    draw.text(((img_w - w) // 2, img_h - margin - (bbox[3] - bbox[1])),
              auth_text, font=font_auth, fill=hex_to_rgb(colors_t["sub"]))


def make_ebook_cover(title, subtitle, theme_name="default", output_path=None):
    """2560×1600px JPEG — standard Kindle."""
    W, H = 2560, 1600
    theme = THEMES.get(theme_name, THEMES["default"])
    img = Image.new("RGB", (W, H), hex_to_rgb(theme["bg"]))
    draw = ImageDraw.Draw(img)
    draw_cover_face(draw, W, H, title, subtitle, "Dott. Sabino Gervasio", theme)

    if not output_path:
        slug = "".join(c if c.isalnum() else "_" for c in title)[:40]
        output_path = OUTPUT_DIR / f"cover_ebook_{slug}.jpg"
    OUTPUT_DIR.mkdir(exist_ok=True)
    img.save(str(output_path), "JPEG", quality=95)
    print(f"  Cover eBook: {output_path} ({W}×{H}px)")
    return str(output_path)


def make_print_cover(title, subtitle, page_count, theme_name="default", output_path=None):
    """
    Full print cover: retro + dorso + fronte (formato 6×9").
    Calcola larghezza dorso con formula KDP B&W carta crema.
    """
    # Formula KDP
    TRIM_W = 6.0    # inches
    TRIM_H = 9.0
    BLEED = 0.125
    DPI = 300
    spine_in = page_count * 0.002252

    total_w_in = (TRIM_W + BLEED) * 2 + spine_in + BLEED * 2
    total_h_in = TRIM_H + BLEED * 2

    px_w = int(total_w_in * DPI)
    px_h = int(total_h_in * DPI)
    spine_px = int(spine_in * DPI)
    face_px = int((TRIM_W + BLEED) * DPI)
    bleed_px = int(BLEED * DPI)

    theme = THEMES.get(theme_name, THEMES["default"])
    img = Image.new("RGB", (px_w, px_h), hex_to_rgb(theme["bg"]))
    draw = ImageDraw.Draw(img)

    # Back cover (left face)
    back_region = img.crop((0, 0, face_px, px_h))
    back_draw = ImageDraw.Draw(back_region)
    draw_cover_face(back_draw, face_px, px_h,
                    f"About {title}", subtitle, "Dott. Sabino Gervasio", theme)
    img.paste(back_region, (0, 0))

    # Spine (center strip)
    spine_x = face_px + bleed_px
    draw.rectangle([(spine_x, 0), (spine_x + spine_px, px_h)],
                   fill=hex_to_rgb(theme["accent"]))
    # Spine title (rotated)
    spine_img = Image.new("RGB", (px_h, max(spine_px, 30)), hex_to_rgb(theme["accent"]))
    spine_d = ImageDraw.Draw(spine_img)
    font_spine = load_font(max(int(spine_px * 0.5), 18))
    spine_text = title[:30]
    bbox = spine_d.textbbox((0, 0), spine_text, font=font_spine)
    tx = (px_h - (bbox[2] - bbox[0])) // 2
    ty = (max(spine_px, 30) - (bbox[3] - bbox[1])) // 2
    spine_d.text((tx, ty), spine_text, font=font_spine, fill=hex_to_rgb(theme["text"]))
    spine_rot = spine_img.rotate(90, expand=True)
    img.paste(spine_rot, (spine_x, 0))

    # Front cover (right face)
    front_x = spine_x + spine_px
    front_region = img.crop((front_x, 0, front_x + face_px, px_h))
    front_draw = ImageDraw.Draw(front_region)
    draw_cover_face(front_draw, face_px, px_h, title, subtitle, "Dott. Sabino Gervasio", theme)
    img.paste(front_region, (front_x, 0))

    if not output_path:
        slug = "".join(c if c.isalnum() else "_" for c in title)[:40]
        output_path = OUTPUT_DIR / f"cover_print_{slug}_{page_count}p.jpg"
    img.save(str(output_path), "JPEG", quality=95, dpi=(DPI, DPI))

    print(f"  Cover print: {output_path}")
    print(f"    Dorso: {spine_in:.3f}\" ({spine_px}px) | Totale: {total_w_in:.2f}\"×{total_h_in:.2f}\"")
    return str(output_path)


def auto_detect_theme(topic):
    topic_lower = topic.lower()
    if any(k in topic_lower for k in ["ai", "python", "codice", "machine", "tech", "software"]):
        return "tech"
    if any(k in topic_lower for k in ["sport", "calcio", "tennis", "atletica"]):
        return "sport"
    if any(k in topic_lower for k in ["scienza", "fisica", "chimica", "matematica"]):
        return "science"
    if any(k in topic_lower for k in ["business", "marketing", "vendite", "lavoro"]):
        return "business"
    if any(k in topic_lower for k in ["storia", "cultura", "arte", "musica", "letteratura"]):
        return "culture"
    return "default"


def generate_covers(title, subtitle, page_count, topic="", theme_name=None):
    OUTPUT_DIR.mkdir(exist_ok=True)
    if not theme_name:
        theme_name = auto_detect_theme(topic or title)
    print(f"  Tema copertina: {theme_name}")
    ebook = make_ebook_cover(title, subtitle, theme_name)
    print_cover = make_print_cover(title, subtitle, page_count, theme_name)
    return {"ebook": ebook, "print": print_cover}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Genera copertine libro")
    p.add_argument("--title", required=True)
    p.add_argument("--subtitle", default="")
    p.add_argument("--pages", type=int, default=100)
    p.add_argument("--topic", default="")
    p.add_argument("--theme", choices=list(THEMES.keys()), default=None)
    args = p.parse_args()
    generate_covers(args.title, args.subtitle, args.pages, args.topic, args.theme)