# Amazon KDP Publishing Metadata Reference

> Last updated: 2026-05 | Source: [KDP Help Center](https://kdp.amazon.com/en_US/help/topic/GHKDSCW2KQ3K4UU4)

---

## Required vs Optional Fields

| Field | Required | Notes |
|-------|----------|-------|
| Title | ✅ | Only the actual title as on cover |
| Author | ✅ | Primary contributor name; pen names allowed |
| Description | ✅ | Used on Amazon product page |
| Keywords | ✅ (recommended) | Up to 7 keywords/phrases |
| Subtitle | ❌ | Title + Subtitle < 200 chars combined |
| Series | ❌ | Not available for low-content books |
| Publisher | ❌ (eBook only) | Your name or publishing company |
| Categories | ❌ (up to 3) | Based on primary audience & marketplace |
| Language | ✅ | Primary marketplace language |
| Primary Audience | ❌ | Reading age / target demographic |
| ISBN | ❌ (eBook) | Not required for eBooks; required for print |

---

## Field Specifications

### Title
- **No character limit stated** (but keep it scannable)
- Must contain **only the actual title** as it appears on cover
- ❌ No promotional language ("bestselling", "free", "new")
- ❌ No repeating generic keywords ("notebook", "journal")
- ❌ No unauthorized trademarks or author references
- ❌ No false contributor references
- ❌ No HTML tags

### Subtitle
- **Title + Subtitle combined must be < 200 characters**
- Contains subordinate title / additional content info
- Follows same rules as Title field

### Author
- **No character limit stated**
- Must be the primary contributor's name
- Pen names allowed, provided they don't impair customer buying decisions
- If name is similar to a popular author, consider adding a middle name or initial
- ❌ No HTML tags

### Book Description (Product Description)

| Rule | Detail |
|------|--------|
| **Max characters** | **4,000** (including HTML tags — bold tags count as chars!) |
| **Recommended length** | ~150 words (~800-1,000 characters) |
| Supported HTML | `<br>`, `<p>`, `<b>`, `<em>`, `<i>`, `<u>`, `<h4>`, `<h5>`, `<h6>`, `<ol>`, `<ul>` |
| ❌ NOT supported | `<h1>`, `<h2>`, `<h3>` |
| ❌ Empty lines | Use two `<br><br>` or `<p></p>`, not multiple spaces |
| ❌ Emojis | Unicode emojis are **not allowed** |
| ❌ URLs/emails | Phone numbers, addresses, websites — all prohibited |
| ❌ Reviews | No quotes from reviewers or testimonials |
| ❌ Promotional | No pricing, availability, "buy now" language |
| ❌ Spoilers | No spoiler information |

**HTML Formatting Quick Reference:**
```
<b>bold text</b>           → Bold
<em>italic text</em>       → Italic
<br>                       → Line break (use two for blank line)
<h4>Section Heading</h4>   → Largest allowed heading
<p>Paragraph text</p>      → Paragraph
<ul><li>Point 1</li><li>Point 2</li></ul>  → Bullet list
<ol><li>Step 1</li><li>Step 2</li></ol>     → Numbered list
```

**Description Structure (Recommended):**
1. Hook — one compelling sentence about who this book is for
2. Problem — what struggle or challenge the reader faces
3. Solution — what the book offers / how it helps
4. What's inside — brief overview of key chapters or takeaways
5. Who this is for — ideal reader profile (1-2 sentences)

### Keywords
- **Up to 7 keywords or short phrases** per book
- 2-3 word phrases recommended (e.g., "single dad", "colonial fiction")
- ❌ No quotation marks around keywords
- ❌ No duplicates (don't repeat info already in title or author name)
- ❌ No subjective claims ("best novel ever", "amazing story")
- ❌ No time-sensitive terms ("new", "on sale", "available now")
- ❌ No generic terms ("book", "novel", "fiction")
- ❌ No spelling errors
- ❌ No other authors' names
- ❌ No Amazon program names ("Kindle Unlimited", "KDP Select")
- ❌ No HTML tags

**Keyword Types to Consider:**
| Type | Examples |
|------|---------|
| Target reader | working mothers, menopausal women, caregivers |
| Condition/Theme | anxiety, burnout, chronic illness, long covid |
| Format/Genre | self-help, guide, handbook |
| Approach | evidence-based, practical, holistic |
| Setting (fiction) | Victorian England, small-town America |
| Tone | uplifting, funny, emotional |

### Categories
- Choose **up to 3 categories** during title setup
- Based on primary audience and marketplace
- Must be relevant to the book's central storyline
- ❌ Inaccurate or manipulative category selection is prohibited

---

## eBook vs Print Differences

| Feature | eBook | Print |
|---------|-------|-------|
| ISBN | Not required | Required (can use free KDP ISBN) |
| Publisher field | Optional | N/A |
| Cover must match metadata | ✅ | ✅ |
| Title must match cover/spine | N/A | ✅ |

---

## Rights & Exclusivity
- You **must own the rights** to publish on KDP
- Enrolling in **KDP Select** makes your eBook **exclusive to Amazon** (cannot sell on other platforms simultaneously)
- If using your own ISBN: title, author name, and binding type must match exactly

---

## Common Rejection Reasons (Avoid These)
1. Description contains URLs, emails, or phone numbers
2. Description contains emojis
3. Title includes promotional language ("bestselling")
4. Keywords include other authors' names (zero-tolerance policy)
5. Cover closely resembles another book's layout, color scheme, or fonts
6. Book description is too short (< 100 words) — hurts discoverability
7. Categories don't match book content

---

## Metadata File Output Format

When generating `kdp-metadata.json`, include all fields with their status:

```json
{
  "title": "",
  "subtitle": "",
  "author": "",
  "description": {
    "html": "<p>...</p>",
    "char_count": 0,
    "has_emoji": false
  },
  "keywords": [],
  "categories": [],
  "language": "English",
  "primary_audience": "",
  "publisher": "",
  "isbn": null,
  "rights": "owned",
  "kdp_select": false,
  "validation": {
    "title_valid": true,
    "subtitle_length_ok": true,
    "description_length_ok": true,
    "no_emoji": true,
    "keyword_count_ok": true,
    "errors": []
  }
}
```