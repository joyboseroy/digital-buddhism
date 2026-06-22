"""
Digital Buddhism - Analysis & Visualisation
============================================
Run after scrape_and_graph.py and scrape_dharmawheel.py.
Produces:
  - Tradition dominance bar chart
  - Bridge teacher ranking table
  - Cross-tradition mention heatmap
  - Summary stats for the paper

Usage:
    python analyse.py
"""

import os
import json
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
from collections import defaultdict

DATA = "data"
FIGS = "figures"
os.makedirs(FIGS, exist_ok=True)

TRADITION_COLOURS = {
    "theravada":  "#b5651d",
    "tibetan":    "#8b0000",
    "zen":        "#2f4f4f",
    "pureland":   "#4b0082",
    "secular":    "#4682b4",
    "vietnamese": "#2e8b57",
    "general":    "#696969",
    "unknown":    "#aaaaaa",
}


# ── 1. Tradition Dominance ────────────────────────────────────────────────────

def plot_tradition_dominance():
    path = os.path.join(DATA, "tradition_counts.csv")
    if not os.path.exists(path):
        print("tradition_counts.csv not found, skipping.")
        return
    df = pd.read_csv(path)
    colours = [TRADITION_COLOURS.get(t, "#aaaaaa") for t in df["tradition"]]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.barh(df["tradition"], df["posts"], color=colours)
    ax.set_xlabel("Number of posts (Reddit)")
    ax.set_title("Tradition Dominance in English-Language Buddhist Reddit\n(r/Buddhism family, 2024–2025)")
    ax.bar_label(bars, padding=3, fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGS, "tradition_dominance.png"), dpi=150)
    plt.close()
    print("Saved: tradition_dominance.png")


# ── 2. Bridge Teacher Ranking ─────────────────────────────────────────────────

def print_bridge_teachers():
    path = os.path.join(DATA, "centrality.csv")
    if not os.path.exists(path):
        print("centrality.csv not found, skipping.")
        return
    df = pd.read_csv(path)
    print("\n── Bridge Teachers (Betweenness Centrality) ──")
    print(df[["teacher", "tradition", "mentions",
              "betweenness_centrality", "degree_centrality"]]
          .head(15).to_string(index=False))

    # Save as latex-ready table for paper
    df.head(15).to_csv(os.path.join(DATA, "bridge_teachers_table.csv"), index=False)


# ── 3. Cross-Tradition Heatmap ────────────────────────────────────────────────

def plot_cross_tradition_heatmap():
    path = os.path.join(DATA, "teacher_mentions.csv")
    if not os.path.exists(path):
        print("teacher_mentions.csv not found, skipping.")
        return
    df = pd.read_csv(path)

    # Pivot: rows = teacher tradition, cols = subreddit tradition
    pivot = (df.groupby(["tradition_teacher", "tradition_sub"])["count"]
               .sum()
               .unstack(fill_value=0))

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(pivot.values, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_yticks(range(len(pivot.index)))
    ax.set_xticklabels(pivot.columns, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(pivot.index, fontsize=9)
    ax.set_title("Teacher Tradition × Subreddit Tradition\n(mention counts)")
    plt.colorbar(im, ax=ax, label="mentions")
    # Annotate cells
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            if val > 0:
                ax.text(j, i, str(int(val)), ha="center", va="center",
                        fontsize=7, color="black")
    plt.tight_layout()
    plt.savefig(os.path.join(FIGS, "cross_tradition_heatmap.png"), dpi=150)
    plt.close()
    print("Saved: cross_tradition_heatmap.png")


# ── 4. Network Graph Visualisation ───────────────────────────────────────────

def plot_teacher_network():
    path = os.path.join(DATA, "teacher_graph.graphml")
    if not os.path.exists(path):
        print("teacher_graph.graphml not found, skipping.")
        return
    G = nx.read_graphml(path)
    if len(G.nodes) < 2:
        print("Graph too small to visualise.")
        return

    # Layout
    pos = nx.spring_layout(G, weight="weight", seed=42, k=2)

    node_colours = [TRADITION_COLOURS.get(
                        G.nodes[n].get("tradition", "unknown"), "#aaaaaa")
                    for n in G.nodes]
    node_sizes   = [max(100, G.nodes[n].get("mentions", 1) * 30)
                    for n in G.nodes]
    edge_weights = [G[u][v].get("weight", 1) for u, v in G.edges]
    max_w = max(edge_weights) if edge_weights else 1
    edge_widths  = [0.5 + 3.0 * w / max_w for w in edge_weights]

    fig, ax = plt.subplots(figsize=(12, 9))
    nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.4,
                           edge_color="#888888", ax=ax)
    nx.draw_networkx_nodes(G, pos, node_color=node_colours,
                           node_size=node_sizes, alpha=0.85, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=7, ax=ax)

    # Legend
    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=col, markersize=10, label=trad)
        for trad, col in TRADITION_COLOURS.items()
        if trad in [G.nodes[n].get("tradition") for n in G.nodes]
    ]
    ax.legend(handles=legend_handles, loc="upper left", fontsize=8)
    ax.set_title("Buddhist Teacher Co-occurrence Network\n"
                 "(node size = mentions; edge weight = co-occurrence in same post)")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(FIGS, "teacher_network.png"), dpi=150)
    plt.close()
    print("Saved: teacher_network.png")


# ── 5. Summary Stats for paper ───────────────────────────────────────────────

def summary_stats():
    print("\n── Summary Statistics ──")
    posts_path = os.path.join(DATA, "posts.csv")
    dw_path    = os.path.join(DATA, "dharmawheel_posts.csv")

    if os.path.exists(posts_path):
        df = pd.read_csv(posts_path)
        print(f"Reddit posts collected:       {len(df)}")
        print(f"Subreddits covered:           {df['subreddit'].nunique()}")
        print(f"Posts with teacher mentions:  {(df['n_teachers'] > 0).sum()}")
        print(f"Unique teachers found:        {df['teachers_mentioned'].apply(json.loads).explode().nunique()}")

    if os.path.exists(dw_path):
        dw = pd.read_csv(dw_path)
        print(f"DharmaWheel topics collected: {len(dw)}")
        print(f"DW topics with teacher mentions: {(dw['n_teachers'] > 0).sum()}")


if __name__ == "__main__":
    summary_stats()
    plot_tradition_dominance()
    print_bridge_teachers()
    plot_cross_tradition_heatmap()
    plot_teacher_network()
    print("\nAll outputs saved to ./figures/")
