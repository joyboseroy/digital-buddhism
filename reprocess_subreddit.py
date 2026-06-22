"""
Subreddit-level teacher co-occurrence graph.
Two teachers are connected if they BOTH appear in the same subreddit.
Edge weight = number of subreddits they share.
This is denser and more meaningful than post-level co-occurrence
when only title text is available.

Run: python3 reprocess_subreddit.py
"""

import json, pandas as pd, networkx as nx, os
from collections import defaultdict
from itertools import combinations

TEACHERS = {
    "Ajahn Chah":           "theravada",
    "Luang Por Chah":       "theravada",
    "Ajahn Brahm":          "theravada",
    "Bhikkhu Bodhi":        "theravada",
    "Thanissaro Bhikkhu":   "theravada",
    "Mahasi Sayadaw":       "theravada",
    "Sayadaw U Tejaniya":   "theravada",
    "Ajahn Sumedho":        "theravada",
    "Ajahn Maha Boowa":     "theravada",
    "Buddhadasa":           "theravada",
    "Buddhaghosa":          "theravada",
    "Thich Nhat Hanh":      "vietnamese",
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
    "Milarepa":             "tibetan",
    "Sogyal Rinpoche":      "tibetan",
    "Shunryu Suzuki":       "zen",
    "Suzuki Roshi":         "zen",
    "Alan Watts":           "zen",
    "Seung Sahn":           "zen",
    "Dogen":                "zen",
    "Bankei":               "zen",
    "Hakuin":               "zen",
    "Dahui":                "zen",
    "Xu Yun":               "zen",
    "Sheng Yen":            "zen",
    "Honen":                "pureland",
    "Shinran":              "pureland",
    "Shandao":              "pureland",
}

TEACHER_NAMES = list(TEACHERS.keys())


def find_teachers(text: str) -> list:
    tl = text.lower()
    found = [n for n in TEACHER_NAMES if n.lower() in tl]
    # deduplicate substrings (e.g. "Suzuki" inside "Shunryu Suzuki")
    found_lower = [f.lower() for f in found]
    return [n for n in found
            if not any(n.lower() != o and n.lower() in o
                       for o in found_lower)]


def main():
    posts_path = "data/posts.csv"
    df = pd.read_csv(posts_path)
    print(f"Loaded {len(df)} posts from {df['subreddit'].nunique()} subreddits.")

    # Re-detect teachers from title (+ selftext if present)
    has_selftext = "selftext" in df.columns
    new_mentions, new_counts = [], []
    for _, row in df.iterrows():
        text = str(row.get("title") or "")
        if has_selftext:
            text += " " + str(row.get("selftext") or "")
        teachers = find_teachers(text)
        new_mentions.append(json.dumps(teachers))
        new_counts.append(len(teachers))
    df["teachers_mentioned"] = new_mentions
    df["n_teachers"] = new_counts
    df.to_csv(posts_path, index=False)

    hit = (df["n_teachers"] > 0).sum()
    print(f"Posts with teacher mentions: {hit} / {len(df)} ({100*hit/len(df):.1f}%)")

    # ── Subreddit-level presence matrix ──────────────────────────────────────
    # teacher → set of subreddits where they appear
    teacher_subs = defaultdict(set)
    teacher_counts = defaultdict(int)

    for _, row in df.iterrows():
        sub = row["subreddit"]
        for t in json.loads(row["teachers_mentioned"]):
            teacher_subs[t].add(sub)
            teacher_counts[t] += 1

    print(f"\nTeachers found: {len(teacher_subs)}")

    # ── Build graph ───────────────────────────────────────────────────────────
    G = nx.Graph()
    for name, subs in teacher_subs.items():
        G.add_node(name,
                   tradition=TEACHERS.get(name, "unknown"),
                   mentions=teacher_counts[name],
                   n_subreddits=len(subs),
                   subreddits=",".join(sorted(subs)))

    # Edge: shared subreddits (weight = number of shared subreddits)
    names = list(teacher_subs.keys())
    for a, b in combinations(names, 2):
        shared = teacher_subs[a] & teacher_subs[b]
        if shared:
            G.add_edge(a, b, weight=len(shared),
                       shared_subs=",".join(sorted(shared)))

    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    nx.write_graphml(G, "data/teacher_graph.graphml")

    # ── Centrality ────────────────────────────────────────────────────────────
    deg  = nx.degree_centrality(G)
    bet  = nx.betweenness_centrality(G, weight="weight")
    clo  = nx.closeness_centrality(G)

    cent = pd.DataFrame([{
        "teacher":                n,
        "tradition":              G.nodes[n].get("tradition"),
        "mentions":               G.nodes[n].get("mentions"),
        "n_subreddits":           G.nodes[n].get("n_subreddits"),
        "degree_centrality":      round(deg[n], 4),
        "betweenness_centrality": round(bet[n], 4),
        "closeness_centrality":   round(clo[n], 4),
    } for n in G.nodes]).sort_values("betweenness_centrality", ascending=False)

    cent.to_csv("data/centrality.csv", index=False)

    print("\n── Bridge teachers (betweenness centrality) ──")
    print(cent.head(15).to_string(index=False))

    # ── Tradition span (how many traditions does each teacher bridge?) ────────
    print("\n── Teachers by subreddit span (most cross-tradition) ──")
    span = cent.sort_values("n_subreddits", ascending=False)
    print(span[["teacher","tradition","mentions","n_subreddits"]].head(15).to_string(index=False))

    # ── Raw mention totals ────────────────────────────────────────────────────
    totals = pd.DataFrame([
        {"teacher": t, "tradition": TEACHERS.get(t,"unknown"),
         "total_mentions": c, "n_subreddits": len(teacher_subs[t])}
        for t, c in teacher_counts.items()
    ]).sort_values("total_mentions", ascending=False)

    totals.to_csv("data/teacher_totals.csv", index=False)
    print("\n── Top 15 by raw mention count ──")
    print(totals.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
