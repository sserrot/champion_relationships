"""Render the Flask page and a portable static demo from one graph snapshot."""

import html
import hashlib
import json
import shutil
from pathlib import Path

from champion_normalization import normalize_name_key


ROOT = Path(__file__).resolve().parent


def build_portfolio(G, partition, image_filename):
    with (ROOT / "data_snapshot.json").open(encoding="utf-8") as file:
        snapshot = json.load(file)

    image_dir = ROOT / "R_analysis" / "img"
    images = {}
    for name in G.nodes:
        filename = image_filename(name)
        if (image_dir / filename).is_file():
            images[name] = filename
        elif (image_dir / filename).with_suffix(".jpg").is_file():
            images[name] = Path(filename).with_suffix(".jpg").name
        else:
            images[name] = None

    nodes = [
        {
            "id": name,
            "faction": G.nodes[name].get("faction") or "",
            "role": G.nodes[name].get("role") or "",
            "community": partition[name],
            "image": images[name],
            "url": G.nodes[name].get("url") or "",
        }
        for name in sorted(G.nodes)
    ]
    edges = [
        {"from": u, "to": v, "relation": attrs["relation"], "evidence": attrs["evidence"]}
        for u, v, attrs in sorted(G.edges(data=True))
    ]
    # Choose a manageable one-hop view for the guided bridge prompt.
    bridge_candidates = [name for name in G.nodes if G.degree(name) <= 25]
    bridge = max(
        bridge_candidates or list(G.nodes),
        key=lambda name: (
            len({partition[neighbor] for neighbor in G.neighbors(name) if partition[neighbor] != partition[name]}),
            sum(partition[neighbor] != partition[name] for neighbor in G.neighbors(name)),
            G.degree(name),
            normalize_name_key(name),
        ),
    )
    graph_data = {"nodes": nodes, "edges": edges, "bridge": bridge}
    shell = (ROOT / "templates" / "network_shell.html").read_text(encoding="utf-8")
    constants = {
        "__SNAPSHOT_LABEL__": html.escape(snapshot["label"]),
        "__CHAMPION_COUNT__": str(G.number_of_nodes()),
        "__RELATIONSHIP_COUNT__": str(G.number_of_edges()),
    }

    def render(image_prefix, css_path, vendor_path, js_path):
        page = shell
        payload = dict(graph_data, imagePrefix=image_prefix)
        constants_for_page = dict(constants, **{
            "__GRAPH_DATA__": json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c"),
            "__CSS_PATH__": css_path,
            "__VENDOR_PATH__": vendor_path,
            "__JS_PATH__": js_path,
        })
        for marker, value in constants_for_page.items():
            page = page.replace(marker, value)
        return page

    def versioned(path, source):
        digest = hashlib.sha256(source.read_bytes()).hexdigest()[:10]
        return f"{path}?v={digest}"

    flask_page = render(
        "/img/",
        versioned("/static/portfolio.css", ROOT / "static" / "portfolio.css"),
        versioned("/static/vendor/vis-network.min.js", ROOT / "static" / "vendor" / "vis-network.min.js"),
        versioned("/static/portfolio.js", ROOT / "static" / "portfolio.js"),
    )
    (ROOT / "templates" / "network.html").write_text(flask_page, encoding="utf-8")

    demo = ROOT / "demo"
    assets = demo / "assets"
    portraits = assets / "img"
    portraits.mkdir(parents=True, exist_ok=True)
    for filename in sorted(set(filter(None, images.values()))):
        shutil.copy2(image_dir / filename, portraits / filename)
    for source, destination in (
        (ROOT / "static" / "portfolio.css", assets / "portfolio.css"),
        (ROOT / "static" / "portfolio.js", assets / "portfolio.js"),
        (ROOT / "static" / "vendor" / "vis-network.min.js", assets / "vis-network.min.js"),
    ):
        shutil.copy2(source, destination)
    static_page = render("assets/img/", "assets/portfolio.css", "assets/vis-network.min.js", "assets/portfolio.js")
    (demo / "index.html").write_text(static_page, encoding="utf-8")
    print(f"Wrote {G.number_of_nodes()} champions and {G.number_of_edges()} connections to templates/network.html and demo/index.html")
