"""
KDP Keyword Extractor
=====================
Extracts high-frequency, high-value keywords from text sources
(course transcripts, competitor descriptions, Amazon reviews).

Author : Alexie Le
GitHub : https://github.com/alexiale123456789
"""

import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter
import re
import os

nltk.download('punkt',      quiet=True)
nltk.download('stopwords',  quiet=True)
nltk.download('punkt_tab',  quiet=True)

# ── KDP-specific noise words to filter out ──────────────────────
KDP_NOISE = {
    'video', 'course', 'going', 'want', 'like', 'just', 'also',
    'make', 'know', 'think', 'really', 'thing', 'people', 'right',
    'good', 'need', 'time', 'actually', 'okay', 'yeah', 'well'
}


def load_text_files(file_paths: list) -> str:
    """Load and concatenate multiple text files."""
    all_text = ""
    for path in file_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                all_text += f.read().lower() + " "
        else:
            print(f"  [WARNING] File not found: {path}")
    return all_text


def clean_text(text: str) -> str:
    """Remove punctuation, numbers, and extra whitespace."""
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_kdp_keywords(text_files: list, top_n: int = 25) -> pd.DataFrame:
    """
    Extract high-frequency keywords from KDP-related text sources.

    Args:
        text_files : List of .txt file paths to analyze
        top_n      : Number of top keywords to return (default 25)

    Returns:
        DataFrame with columns: Keyword, Frequency, Relevance_Score

    Example:
        files = ["transcript_01.txt", "transcript_02.txt"]
        df = extract_kdp_keywords(files, top_n=20)
        print(df)
        df.to_csv("keyword_report.csv", index=False)
    """
    print(f"\n{'='*50}")
    print("  KDP KEYWORD EXTRACTOR")
    print(f"{'='*50}")
    print(f"  Analyzing {len(text_files)} file(s)...")

    raw_text   = load_text_files(text_files)
    clean      = clean_text(raw_text)

    tokens     = word_tokenize(clean)
    stop_words = set(stopwords.words('english')) | KDP_NOISE
    filtered   = [w for w in tokens if w not in stop_words and len(w) > 3]

    freq       = Counter(filtered).most_common(top_n)
    df         = pd.DataFrame(freq, columns=['Keyword', 'Frequency'])
    df['Relevance_Score'] = (df['Frequency'] / df['Frequency'].max()).round(2)

    print(f"  Total tokens processed : {len(tokens):,}")
    print(f"  Unique keywords found  : {len(set(filtered)):,}")
    print(f"  Top {top_n} keywords extracted\n")
    return df


def score_niche_keywords(keywords_df: pd.DataFrame,
                          high_value_terms: list) -> pd.DataFrame:
    """
    Boost relevance score for known high-value KDP niche terms.

    Args:
        keywords_df      : Output from extract_kdp_keywords()
        high_value_terms : List of manually defined important terms

    Returns:
        DataFrame sorted by boosted Relevance_Score
    """
    df = keywords_df.copy()
    boost = df['Keyword'].isin([t.lower() for t in high_value_terms])
    df.loc[boost, 'Relevance_Score'] = (df.loc[boost, 'Relevance_Score'] * 1.5).clip(upper=1.0)
    df['Boosted'] = boost
    return df.sort_values('Relevance_Score', ascending=False).reset_index(drop=True)


# ── Demo run ─────────────────────────────────────────────────────
if __name__ == "__main__":
    # Demo with synthetic text if no files are provided
    DEMO_TEXT = """
    Publishing on Amazon KDP requires understanding keyword research
    and niche selection. Successful authors focus on low competition
    niches with high demand. The royalty structure on KDP rewards
    strategic pricing between 2.99 and 9.99 dollars. Building
    reviews volume is more important than chasing perfect ratings.
    Self publishing with AI tools like ChatGPT helps with content
    creation and outline generation. Low content books like journals
    planners and notebooks are great for beginners. Keyword
    optimization in your book title subtitle and description drives
    organic discovery on Amazon search. Print on demand with KDP
    allows publishing paperback books without inventory risk.
    Successful authors iterate through multiple versions based on
    reader feedback and review analysis.
    """

    # Write demo file
    with open("demo_transcript.txt", "w") as f:
        f.write(DEMO_TEXT * 5)

    df = extract_kdp_keywords(["demo_transcript.txt"], top_n=15)

    # Boost known KDP terms
    kdp_terms = ['keyword', 'niche', 'royalty', 'publishing', 'review',
                 'pricing', 'content', 'amazon', 'title', 'description']
    df_scored = score_niche_keywords(df, kdp_terms)

    print(df_scored.to_string(index=False))
    df_scored.to_csv("sample_keywords.csv", index=False)
    print("\n  Saved → sample_keywords.csv")

    # Cleanup demo file
    os.remove("demo_transcript.txt")