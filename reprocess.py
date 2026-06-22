"""
Reprocess existing posts.csv with expanded teacher list.
Searches BOTH title and any stored body text.

Run: python3 reprocess.py
"""

import json, pandas as pd, networkx as nx, os
from collections import defaultdict
from itertools import combinations

# Clean dict — no duplicate keys, Thich Nhat Hanh = vietnamese only
TEACHERS = {
    # Theravada
    "Ajahn Chah":           "theravada",
    "Luang Por Chah":       "theravada",
    "Ajahn Brahm":          "theravada",
    "Bhikkhu Bodhi":        "theravada",
    "Thanissaro Bhikkhu":   "theravada",
    "Mahasi Sayadaw":       "theravada",
    "Sayadaw U Tejaniya":   "theravada",
    "Ajahn Sumedho":        "theravada",
    "Ajahn Maha Boowa":     "theravada",
    "Bhikkhu Analayo":      "theravada",
    "Yuttadhammo":          "theravada",
    "Nyanatiloka":          "theravada",
    "Buddhadasa":           "theravada",
    "Buddhaghosa":          "theravada",
    # Vietnamese
    "Thich Nhat Hanh":      "vietnamese",
    # Secular / IMS
    "Shinzen Young":        "secular",
    "Jack Kornfield":       "secular",
    "Joseph Goldstein":     "secular",
    "Sharon Salzberg":      "secular",
    "Tara Brach":           "secular",
    "Sam Harris":           "secular",
    "Rob Burbea":           "secular",
    "Culadasa":             "secular",
    "Leigh Brasington":     "secular",
    "Gil Fronsdal":         "secular",
    "Rupert Spira":         "secular",
    "Michael Taft":         "secular",
    # Tibetan
    "Mingyur Rinpoche":     "tibetan",
    "Pema Chodron":         "tibetan",
    "Dalai Lama":           "tibetan",
    "Chogyam Trungpa":      "tibetan",
    "Tsoknyi Rinpoche":     "tibetan",
    "Dilgo Khyentse":       "tibetan",
    "Khenchen Pema Sherab": "tibetan",
    "Dudjom Rinpoche":      "tibetan",
    "Dudjom Lingpa":        "tibetan",
    "Karma Chagme":         "tibetan",
    "Longchenpa":           "tibetan",
    "Patrul Rinpoche":      "tibetan",
    "Nagarjuna":            "tibetan",
    "Shantideva":           "tibetan",
    "Niguma":               "tibetan",
    "Machig Labdron":       "tibetan",
    "Milarepa":             "tibetan",
    "Naropa":               "tibetan",
    "Tilopa":               "tibetan",
    "Penor Rinpoche":       "tibetan",
    "Sogyal Rinpoche":      "tibetan",
    "Vasubandhu":           "tibetan",
    "Asanga":               "tibetan",
    "Chandrakirti":         "tibetan",
    # Zen / Chan
    "Shunryu Suzuki":       "zen",
    "Suzuki Roshi":         "zen",
    "Alan Watts":           "zen",
    "Seung Sahn":           "zen",
    "John Daido Loori":     "zen",
    "Hakuun Yasutani":      "zen",
    "Taizan Maezumi":       "zen",
    "Huang Po":             "zen",
    "Linji":                "zen",
    "Dahui":                "zen",
    "Dogen":                "zen",
    "Bankei":               "zen",
    "Hakuin":               "zen",
    "Xu Yun":               "zen",
    "Sheng Yen":            "zen",     # Master Sheng Yen — single entry
    # Pure Land
    "Honen":                "pureland",
    "Shinran":              "pureland",
    "Rennyo":               "pureland",
    "Shandao":              "pureland",
}

TEACHER_NAMES = list(TEACHERS.keys())


def find_teachers(text: str) -> list:
    tl = text.lower()
    found = []
    for n in TEACHER_NAMES:
        if n.lower() in tl:
            # avoid "Master Sheng Yen" double-counting with "Sheng Yen"
            found.append(n)
    # deduplicate: if both "Sheng Yen" and "Master Sheng Yen" found, keep longer
    clean = []
    found_lower = [f.lower() for f in found]
    for n in found:
        dominated = any(n.lower() != o and n.lower() in o for o in found_lower)
        if not dominated:
            clean.append(n)
    return clean


def reprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Re-run teacher detection on title + selftext columns."""
    df = df.copy()
    # handle both 'selftext' column (from PullPush) and missing column
    has_selftext = "selftext" in df.columns

    new_mentions, new_counts = [], []
    for _, row in df.iterrows():
        title = str(row.get("title") or "")
        body  = str(row.get("selftext") or "") if has_selftext else ""
        text  = title + " " + body
        teachers = find_teachers(text)
        new_mentions.append(json.dumps(teachers))
        new_counts.append(len(teachers))

    df["teachers_mentioned"] = new_mentions
    df["n_teachers"] = new_counts
    return df


def build_teacher_mention_counts(df):
    rows = []
    for _, row in df.iterrows():
        for t in json.loads(row["teachers_mentioned"]):
            rows.append({
                "teacher":           t,
                "tradition_teacher": TEACHERS.get(t, "unknown"),
                "subreddit":         row["subreddit"],
                "tradition_sub":     row["tradition"],
            })
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
            weights[tuple(sorted([a, b]))] += 1
    for (a, b), w in weights.items():
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
        "tradition":              G.nodes[n].get("tradition", "unknown"),
        "mentions":               G.nodes[n].get("mentions", 0),
        "degree_centrality":      round(deg[n], 4),
        "betweenness_centrality": round(bet[n], 4),
        "closeness_centrality":   round(clo[n], 4),
    } for n in G.nodes]).sort_values("betweenness_centrality", ascending=False)


def main():
    posts_path = "data/posts.csv"
    if not os.path.exists(posts_path):
        print("No posts.csv found. Run scrape_and_graph.py first.")
        return

    df = pd.read_csv(posts_path)
    print(f"Loaded {len(df)} posts.")
    print(f"Columns: {list(df.columns)}")

    print("Reprocessing with expanded teacher list...")
    df = reprocess(df)
    df.to_csv(posts_path, index=False)

    hit = (df["n_teachers"] > 0).sum()
    print(f"Posts with teacher mentions: {hit} / {len(df)} ({100*hit/len(df):.1f}%)")

    mentions = build_teacher_mention_counts(df)
    if not mentions.empty:
        mentions.to_csv("data/teacher_mentions.csv", index=False)

    G = build_teacher_graph(df)
    print(f"Teacher graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    nx.write_graphml(G, "data/teacher_graph.graphml")

    cent = compute_centrality(G)
    if not cent.empty:
        cent.to_csv("data/centrality.csv", index=False)
        print("\nBridge teachers (betweenness centrality):")
        print(cent.head(15).to_string(index=False))

    totals = (mentions.groupby("teacher")["count"].sum()
              .reset_index().sort_values("count", ascending=False))
    print("\nTop 15 by raw mention count:")
    print(totals.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
