"""
Digital Buddhism Network Scraper - APPEND MODE
================================================
Appends new posts to existing data/posts.csv on each run.
No login required. Tries PullPush then RSS fallback.

Run: python3 scrape_and_graph.py
"""

import time, json, requests, pandas as pd, networkx as nx, os
from collections import defaultdict
from itertools import combinations

HEADERS = {"User-Agent": "academic_buddhism_network_study/0.1 (non-commercial research)"}

SUBREDDITS = {
    "Buddhism":        "general",
    "Zen":             "zen",
    "TibetanBuddhism": "tibetan",
    "vajrayana":       "tibetan",
    "theravada":       "theravada",
    "vipassana":       "theravada",
    "PureLand":        "pureland",
    "Chan":            "zen",
    "secularbuddhism": "secular",
    "streamentry":     "theravada",
    "Dzogchen":        "tibetan",
    "zen":             "zen",
}

TEACHERS = {
    "Ajahn Chah":           "theravada",
    "Ajahn Brahm":          "theravada",
    "Bhikkhu Bodhi":        "theravada",
    "Thanissaro Bhikkhu":   "theravada",
    "Mahasi Sayadaw":       "theravada",
    "Sayadaw U Tejaniya":   "theravada",
    "Ajahn Sumedho":        "theravada",
    "Thich Nhat Hanh":      "vietnamese",
    "Mingyur Rinpoche":     "tibetan",
    "Pema Chodron":         "tibetan",
    "Dalai Lama":           "tibetan",
    "Chogyam Trungpa":      "tibetan",
    "Tsoknyi Rinpoche":     "tibetan",
    "Dilgo Khyentse":       "tibetan",
    "Khenchen Pema Sherab": "tibetan",
    "Shunryu Suzuki":       "zen",
    "Alan Watts":           "zen",
    "Seung Sahn":           "zen",
    "Shinzen Young":        "secular",
    "Jack Kornfield":       "secular",
    "Joseph Goldstein":     "secular",
    "Sharon Salzberg":      "secular",
    "Tara Brach":           "secular",
    "Sam Harris":           "secular",
    "Honen":                "pureland",
    "Shinran":              "pureland",
}

TEACHER_NAMES = list(TEACHERS.keys())


def find_teachers(text: str) -> list:
    tl = text.lower()
    return [n for n in TEACHER_NAMES if n.lower() in tl]


def fetch_pullpush(subreddit: str, limit: int = 200) -> list:
    rows = []
    base = "https://api.pullpush.io/reddit/search/submission/"
    before = None
    while len(rows) < limit:
        params = {"subreddit": subreddit, "size": 100,
                  "sort": "desc", "sort_type": "score"}
        if before:
            params["before"] = before
        try:
            r = requests.get(base, params=params, headers=HEADERS, timeout=30)
            if r.status_code != 200:
                print(f"    PullPush HTTP {r.status_code}")
                return rows
            data = r.json().get("data", [])
            if not data:
                break
            for p in data:
                body = (p.get("title") or "") + " " + (p.get("selftext") or "")
                teachers = find_teachers(body)
                rows.append({
                    "post_id":            p.get("id"),
                    "subreddit":          subreddit,
                    "title":              p.get("title"),
                    "selftext":           (p.get("selftext") or "")[:2000],
                    "score":              p.get("score", 0),
                    "num_comments":       p.get("num_comments", 0),
                    "created_utc":        p.get("created_utc"),
                    "teachers_mentioned": json.dumps(teachers),
                    "n_teachers":         len(teachers),
                })
            before = data[-1].get("created_utc")
            time.sleep(1)
        except Exception as e:
            print(f"    PullPush error: {e}")
            break
    return rows


def fetch_rss(subreddit: str) -> list:
    import xml.etree.ElementTree as ET
    url = f"https://old.reddit.com/r/{subreddit}/top/.rss?t=year"
    rows = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return rows
        root = ET.fromstring(r.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            title   = entry.findtext("atom:title",   default="", namespaces=ns)
            content = entry.findtext("atom:content", default="", namespaces=ns)
            body = title + " " + content
            teachers = find_teachers(body)
            rows.append({
                "post_id":            entry.findtext("atom:id", default="", namespaces=ns),
                "subreddit":          subreddit,
                "title":              title,
                "score":              0,
                "num_comments":       0,
                "created_utc":        None,
                "teachers_mentioned": json.dumps(teachers),
                "n_teachers":         len(teachers),
            })
    except Exception as e:
        print(f"    RSS error: {e}")
    return rows


def scrape_all(existing_ids: set) -> pd.DataFrame:
    all_rows = []
    for sub, tradition in SUBREDDITS.items():
        print(f"  r/{sub} ({tradition})...")
        rows = []

        print("    trying PullPush...", end=" ", flush=True)
        rows = fetch_pullpush(sub, limit=200)
        if rows:
            print(f"{len(rows)} posts")
        else:
            print("0  trying RSS fallback...", end=" ", flush=True)
            rows = fetch_rss(sub)
            print(f"{len(rows)} posts (RSS only)")

        # tag tradition and filter already-collected posts
        new_rows = []
        for r in rows:
            r["tradition"] = tradition
            if r.get("post_id") and r["post_id"] not in existing_ids:
                new_rows.append(r)

        print(f"    {len(new_rows)} new posts (after dedup)")
        all_rows.extend(new_rows)
        time.sleep(2)

    return pd.DataFrame(all_rows)


def build_teacher_mention_counts(df):
    rows = []
    for _, row in df.iterrows():
        for t in json.loads(row["teachers_mentioned"]):
            rows.append({"teacher": t,
                         "tradition_teacher": TEACHERS.get(t, "unknown"),
                         "subreddit": row["subreddit"],
                         "tradition_sub": row["tradition"]})
    if not rows:
        return pd.DataFrame()
    return (pd.DataFrame(rows)
            .groupby(["teacher","tradition_teacher","subreddit","tradition_sub"])
            .size().reset_index(name="count"))


def build_teacher_graph(df):
    G = nx.Graph()
    totals = defaultdict(int)
    for _, row in df.iterrows():
        for t in json.loads(row["teachers_mentioned"]):
            totals[t] += 1
    for name, trad in TEACHERS.items():
        if totals[name] > 0:
            G.add_node(name, tradition=trad, mentions=totals[name])
    weights = defaultdict(int)
    for _, row in df.iterrows():
        ts = list(set(json.loads(row["teachers_mentioned"])))
        for a, b in combinations(ts, 2):
            weights[tuple(sorted([a,b]))] += 1
    for (a,b), w in weights.items():
        if G.has_node(a) and G.has_node(b):
            G.add_edge(a, b, weight=w)
    return G


def compute_centrality(G):
    if len(G.nodes) < 2:
        return pd.DataFrame()
    deg = nx.degree_centrality(G)
    bet = nx.betweenness_centrality(G, weight="weight")
    clo = nx.closeness_centrality(G)
    return pd.DataFrame([{
        "teacher":                n,
        "tradition":              G.nodes[n].get("tradition","unknown"),
        "mentions":               G.nodes[n].get("mentions",0),
        "degree_centrality":      round(deg[n],4),
        "betweenness_centrality": round(bet[n],4),
        "closeness_centrality":   round(clo[n],4),
    } for n in G.nodes]).sort_values("betweenness_centrality", ascending=False)


def tradition_dominance(df):
    return (df.groupby("tradition")
              .agg(posts=("post_id","count"),
                   total_score=("score","sum"),
                   total_comments=("num_comments","sum"))
              .reset_index().sort_values("posts", ascending=False))


def main():
    os.makedirs("data", exist_ok=True)
    posts_path = "data/posts.csv"

    # Load existing data if present
    if os.path.exists(posts_path):
        existing = pd.read_csv(posts_path)
        existing_ids = set(existing["post_id"].dropna().astype(str))
        print(f"Loaded {len(existing)} existing posts ({len(existing_ids)} unique IDs).")
    else:
        existing = pd.DataFrame()
        existing_ids = set()

    print("Scraping new posts...")
    new_df = scrape_all(existing_ids)
    print(f"\nNew posts this run: {len(new_df)}")

    # Merge and save
    if not new_df.empty:
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset="post_id")
    else:
        combined = existing

    combined.to_csv(posts_path, index=False)
    print(f"Total posts in dataset: {len(combined)}")

    if combined.empty:
        print("No data yet.")
        return

    # Rebuild everything from full combined dataset
    trad = tradition_dominance(combined)
    trad.to_csv("data/tradition_counts.csv", index=False)
    print("\nTradition dominance:")
    print(trad.to_string(index=False))

    mentions = build_teacher_mention_counts(combined)
    if not mentions.empty:
        mentions.to_csv("data/teacher_mentions.csv", index=False)

    G = build_teacher_graph(combined)
    print(f"\nTeacher graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    nx.write_graphml(G, "data/teacher_graph.graphml")

    cent = compute_centrality(G)
    if not cent.empty:
        cent.to_csv("data/centrality.csv", index=False)
        print("\nBridge teachers (betweenness centrality):")
        print(cent.head(10).to_string(index=False))

    print("\nDone. Outputs in ./data/")


if __name__ == "__main__":
    main()
