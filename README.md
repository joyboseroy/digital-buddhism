# Digital Buddhism: A Network Analysis of Teacher References on Reddit

Companion code for the Medium article:
[Why Alan Watts Connects More Buddhist Communities Online Than Most Buddhist Masters](https://joyboseroy.medium.com/why-alan-watts-connects-more-buddhist-communities-online-than-most-buddhist-masters-63f62445d33a)

## What this does

Scrapes Buddhist subreddits via the PullPush API (no login needed),
builds a teacher co-presence network, and computes betweenness centrality
to identify which teachers bridge tradition boundaries online.

## Key finding

Being mentioned a lot is not the same as being a bridge.

| Teacher | Mentions | Subreddits | Betweenness |
|---|---|---|---|
| Longchenpa | 10 | 4 | 0.27 |
| Alan Watts | 7 | 4 | 0.17 |
| Ajahn Chah | 14 | 3 | 0.13 |
| Dalai Lama | 39 | 5 | 0.10 |
| Dilgo Khyentse | 14 | 4 | 0.07 |
| Culadasa | 18 | 1 | 0.00 |
| Rob Burbea | 10 | 1 | 0.00 |
| Thanissaro Bhikkhu | 9 | 1 | 0.00 |

The Dalai Lama has the most mentions but low betweenness. Alan Watts,
who died in 1973 and held no lineage transmission, has higher betweenness
centrality than every living teacher in the dataset.

## Tradition dominance (1,804 posts across 12 subreddits)

| Tradition | Posts |
|---|---|
| Theravada | 558 |
| Tibetan | 524 |
| Zen | 314 |
| Secular | 159 |
| General | 125 |
| Pure Land | 124 |

Pure Land represents the majority tradition across Japan, China, and Korea.
124 posts with almost no crossover presence.

## Run it

```bash
pip install -r requirements.txt

python3 scrape_and_graph.py      # collect data
python3 reprocess_subreddit.py   # build subreddit-level graph
python3 analyse.py               # generate figures
```

## Apply it to a different domain

Change `SUBREDDITS` and `TEACHERS` in `reprocess_subreddit.py`
to any domain you want. Same pipeline works for philosophy,
yoga traditions, political communities, anything with named figures.

## Data

Data is not committed. Run `scrape_and_graph.py` to collect fresh data.
PullPush API is free and requires no credentials.

## Why this matters for AI

LLMs trained on internet text inherit the skew visible in this data.
A model asked about Buddhism will overrepresent Tibetan and Zen perspectives
and underrepresent Theravada, Pure Land, and Chinese Chan traditions.
Network analysis of online discourse is one way to map these gaps
before they get baked into a model.
