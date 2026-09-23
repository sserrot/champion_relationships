# Champion Connections

An interactive map of relationships between League of Legends champions, built as a personal network analysis project. Start with one champion, follow their immediate connections, explore a region, or open the full graph.

**Region map** places every champion in the selected region inside one circle and shows directly linked champions from the two strongest neighboring regions (one on narrow screens). Neighboring regions are ranked by visible connections, with newer `related` evidence weighted highest. The relationship filter and hidden champions also apply to this view.

Use **Hide champions** to remove nodes and their connections in any view. Select a hidden name to restore it, or use **Show all hidden**.

## Try it

Open [`demo/index.html`](demo/index.html) in a browser. The `demo/` folder includes the portraits, styles, script, and a pinned copy of vis-network 9.1.9. It does not require Flask or a CDN. To run the same page locally through Flask:

```powershell
pip install -r requirements.txt
python server.py
```

Visit `http://127.0.0.1:5001/`. Compare the previous interactive graph at `/previous`. The earlier R analysis report remains available at `/report`.

## Read the graph carefully

The displayed data is a dated League Universe snapshot, labeled on the page. Broad `related` links, region, and role come from its current champion pages; `related` does not necessarily mean friendship. Friend and rival labels come from the older League Universe site. Some pairs have both labels and appear as **friend + rival**. Kled's broad rival list is retained as recorded. The Universe roster includes Norra, who is absent from the PC game roster in Data Dragon 16.18.1.

Links are undirected, and an absent link is not evidence that two champions are unrelated. “Who connects groups?” picks a champion linked to many detected network clusters, limiting candidates to 25 connections so the starting view stays readable. The clusters are an analysis result, not official factions.

## Data and build workflow

`champions_canonical.json` is the checked-in source for the broad graph. `champions_updated.json` holds the reviewed League Universe records; `champions_new.json` is the older fallback. `champions.json` supplies the older friend/rival labels and is not changed by a refresh. The original [Scrapy spider](champion_relationships/spiders/champions_spider.py) and [R analysis](R_analysis/network_graph.Rmd) document earlier phases of this project.

To check the live League Universe roster and stage a full refresh:

```powershell
python fetch_champion_data.py
```

Review `data_refresh/manifest.json`, `data_refresh/changes.csv`, and `data_refresh/champions_review.json`. The script checks Riot's Data Dragon game roster against the League Universe browse list and records Universe-only champions separately. After reviewing an issue-free batch, apply it and rebuild both outputs:

```powershell
python fetch_champion_data.py --apply-reviewed --rebuild-graph
```

Applying checks that the canonical file and reviewed batch are unchanged since staging, updates `data_snapshot.json`, and leaves the old friend/rival labels intact. `community_analysis.py` types edges and detects communities; `portfolio_render.py` writes `templates/network.html` for Flask and `demo/index.html` for static hosting. Edit `templates/network_shell.html`, `static/portfolio.css`, or `static/portfolio.js`, then run `python community_analysis.py` to refresh generated files.

Run focused checks with `python -m unittest discover -s tests`.

Run `python champ_img_download.py` before rebuilding to fill missing portraits. It uses current Riot Data Dragon icons for game champions and League Universe images for Universe-only champions. `portrait_sources.json` records each new asset's source and hash.

Champion Connections is not endorsed by Riot Games and does not reflect the views of Riot Games or anyone involved in producing League of Legends. League of Legends and Riot Games are trademarks or registered trademarks of Riot Games, Inc. League of Legends © Riot Games, Inc.
