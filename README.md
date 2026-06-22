# Digital Buddhism: A Network Analysis of Teacher References on Reddit

[Why Alan Watts Connects More Buddhist Communities Online Than Most Buddhist Masters](https://joyboseroy.medium.com/why-alan-watts-connects-more-buddhist-communities-online-than-most-buddhist-masters-63f62445d33a)

## What this does

Scrapes Buddhist subreddits via the PullPush API (no login needed),
builds a teacher co-presence network, and computes betweenness centrality
to identify which teachers bridge tradition boundaries online.

## Run it

pip install -r requirements.txt

python3 scrape_and_graph.py      # collect data
python3 reprocess_subreddit.py   # build subreddit-level graph
python3 analyse.py               # generate figures

## Apply it to a different domain

Change SUBREDDITS and TEACHERS in reprocess_subreddit.py
to any domain you want. Same pipeline works for philosophy,
yoga traditions, political communities, anything with named figures.

## Data

Data is not committed. Run scrape_and_graph.py to collect fresh data.
PullPush API is free and requires no credentials.
