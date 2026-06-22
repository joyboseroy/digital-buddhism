"""
DharmaWheel Forum Scraper
==========================
Scrapes DharmaWheel (dharmawheel.net) forum posts without an API.
Focuses on subforum structure to map which traditions are active
and which teachers get discussed where.

Usage:
    python scrape_dharmawheel.py

Output:
    data/dharmawheel_posts.csv
    data/dharmawheel_teacher_mentions.csv
"""

import time
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from collections import defaultdict

HEADERS = {
    "User-Agent": "Mozilla/5.0 (academic research bot; contact: joyboseroy@gmail.com)"
}

BASE_URL = "https://www.dharmawheel.net"

# Subforums and their tradition mapping
SUBFORUMS = {
    "/viewforum.php?f=1":  "tibetan",      # Tibetan Buddhism
    "/viewforum.php?f=2":  "zen",          # Zen / Chan
    "/viewforum.php?f=3":  "theravada",    # Theravada
    "/viewforum.php?f=40": "pureland",     # Pure Land
    "/viewforum.php?f=9":  "general",      # General Buddhism
    "/viewforum.php?f=46": "secular",      # Secular / Science
}

PAGES_PER_FORUM = 5   # each page ~25 topics; 5 pages = ~125 topics per subforum

TEACHERS = [
    "Ajahn Chah", "Ajahn Brahm", "Bhikkhu Bodhi", "Thanissaro Bhikkhu",
    "Mahasi Sayadaw", "Sayadaw U Tejaniya", "Ajahn Sumedho",
    "Thich Nhat Hanh", "Mingyur Rinpoche", "Pema Chodron",
    "Dalai Lama", "Chogyam Trungpa", "Tsoknyi Rinpoche",
    "Dilgo Khyentse", "Patrul Rinpoche", "Khenchen Pema Sherab",
    "Shunryu Suzuki", "Alan Watts", "Seung Sahn", "Shinzen Young",
    "Jack Kornfield", "Joseph Goldstein", "Sharon Salzberg", "Tara Brach",
]


def find_teachers(text: str) -> list:
    text_lower = text.lower()
    return [t for t in TEACHERS if t.lower() in text_lower]


def get_soup(url: str, retries=3) -> BeautifulSoup | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return BeautifulSoup(r.text, "html.parser")
            print(f"  HTTP {r.status_code} for {url}")
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
        time.sleep(2 ** attempt)
    return None


def scrape_forum_page(forum_path: str, tradition: str, page: int) -> list:
    start = page * 25
    url = BASE_URL + forum_path + f"&start={start}"
    soup = get_soup(url)
    if not soup:
        return []

    rows = []
    # DharmaWheel uses phpBB; topic links are in <a> tags with class containing "topictitle"
    for topic_link in soup.find_all("a", class_=lambda c: c and "topictitle" in c):
        title = topic_link.get_text(strip=True)
        href  = topic_link.get("href", "")
        teachers = find_teachers(title)
        rows.append({
            "source":    "dharmawheel",
            "tradition": tradition,
            "title":     title,
            "url":       BASE_URL + "/" + href.lstrip("/"),
            "teachers_mentioned": json.dumps(teachers),
            "n_teachers": len(teachers),
        })
    return rows


def scrape_dharmawheel() -> pd.DataFrame:
    all_rows = []
    for forum_path, tradition in SUBFORUMS.items():
        print(f"  Scraping DharmaWheel {forum_path} ({tradition})...")
        for page in range(PAGES_PER_FORUM):
            rows = scrape_forum_page(forum_path, tradition, page)
            all_rows.extend(rows)
            time.sleep(1.5)   # polite delay
        print(f"    {len(all_rows)} topics so far")
    return pd.DataFrame(all_rows)


def teacher_mention_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        for t in json.loads(row["teachers_mentioned"]):
            rows.append({"teacher": t, "tradition": row["tradition"]})
    if not rows:
        return pd.DataFrame()
    return (pd.DataFrame(rows)
            .groupby(["teacher", "tradition"])
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False))


if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)

    print("Scraping DharmaWheel...")
    df = scrape_dharmawheel()
    df.to_csv("data/dharmawheel_posts.csv", index=False)
    print(f"Collected {len(df)} topics.")

    summary = teacher_mention_summary(df)
    if not summary.empty:
        summary.to_csv("data/dharmawheel_teacher_mentions.csv", index=False)
        print("\nTop teacher mentions on DharmaWheel:")
        print(summary.head(20).to_string(index=False))
