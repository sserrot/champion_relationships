"""
Community detection and interactive visualization for League of Legends champion relationships.
Uses NetworkX for graph analysis (Louvain community detection) and Pyvis for interactive visualization.
"""

import json
import networkx as nx
from pyvis.network import Network

# Faction color mapping
FACTION_COLORS = {
    "Freljord": "#5BC0EB",
    "Ionia": "#E8528A",
    "Noxus": "#C1292E",
    "Shurima": "#F0C808",
    "Zaun": "#39FF14",
    "Piltover": "#FFB627",
    "Bilgewater": "#5E4B3B",
    "Demacia": "#0077B6",
    "Bandle City": "#A06CD5",
    "BandleCity": "#A06CD5",
    "Shadow Isles": "#2D6A4F",
    "ShadowIsles": "#2D6A4F",
    "The Void": "#6A0572",
    "Void": "#6A0572",
    "Targon": "#FCA311",
    "MtTargon": "#FCA311",
    "Ixtal": "#57CC99",
    "Runeterra": "#888888",
    "Independent": "#AAAAAA",
    "": "#CCCCCC",
}

# Community colors (for detected communities)
COMMUNITY_COLORS = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#42d4f4", "#f032e6", "#bfef45", "#fabed4",
    "#469990", "#dcbeff", "#9A6324", "#fffac8", "#800000",
    "#aaffc3", "#808000", "#ffd8b1", "#000075", "#a9a9a9",
]


def load_data_new(path="champions_new.json"):
    """Load the newer dataset which has region/related/race/role fields."""
    with open(path) as f:
        data = json.load(f)

    champions = {}
    for entry in data:
        name = entry["champion_name"][0]
        champions[name] = {
            "region": entry.get("region", [""])[0],
            "related": [r for r in entry.get("related", [""]) if r],
            "race": entry.get("race", [""])[0],
            "role": entry.get("role", [""])[0],
        }
    return champions


def load_data_old(path="champions.json"):
    """Load the older dataset which has friends/rivals/faction fields."""
    with open(path) as f:
        data = json.load(f)

    champions = {}
    for entry in data:
        name = entry["champion_name"][0]
        champions[name] = {
            "faction": entry.get("faction", [""])[0],
            "friends": [r for r in entry.get("friends", [""]) if r],
            "rivals": [r for r in entry.get("rivals", [""]) if r],
        }
    return champions


def build_graph(champions_new, champions_old):
    """Build a NetworkX graph combining both datasets."""
    G = nx.Graph()

    # Add all champions as nodes with attributes
    for name, data in champions_new.items():
        faction = data["region"]
        # Try to get faction from old data if available
        old_name_variants = [name, name.replace(" ", ""), name.replace("'", "")]
        old_data = None
        for v in old_name_variants:
            if v in champions_old:
                old_data = champions_old[v]
                break

        old_faction = old_data["faction"] if old_data else ""
        display_faction = faction if faction else old_faction

        G.add_node(name, faction=display_faction, role=data["role"], race=data["race"])

    # Add edges from new dataset (related = general relationship)
    for name, data in champions_new.items():
        for related in data["related"]:
            if related in G.nodes:
                G.add_edge(name, related, relation="related")

    # Add edges from old dataset (friends and rivals)
    for old_name, data in champions_old.items():
        # Find matching node in graph
        match = None
        for node in G.nodes:
            if node == old_name or node.replace(" ", "") == old_name or node.replace("'", "") == old_name:
                match = node
                break
        if not match:
            continue

        for friend in data.get("friends", []):
            # Find friend node
            for node in G.nodes:
                if node == friend or node.replace(" ", "") == friend or node.replace("'", "") == friend:
                    if not G.has_edge(match, node):
                        G.add_edge(match, node, relation="friend")
                    break

        for rival in data.get("rivals", []):
            for node in G.nodes:
                if node == rival or node.replace(" ", "") == rival or node.replace("'", "") == rival:
                    if not G.has_edge(match, node):
                        G.add_edge(match, node, relation="rival")
                    break

    # Remove isolated nodes for cleaner visualization
    isolates = list(nx.isolates(G))
    G.remove_nodes_from(isolates)

    return G


def detect_communities(G):
    """Run Louvain community detection."""
    communities = nx.community.louvain_communities(G, seed=42)
    # Convert to node -> community_id mapping
    partition = {}
    for i, comm in enumerate(communities):
        for node in comm:
            partition[node] = i
    return partition, communities


def print_community_report(G, partition, communities):
    """Print a summary of detected communities."""
    print(f"\n{'='*60}")
    print(f"COMMUNITY DETECTION REPORT")
    print(f"{'='*60}")
    print(f"Champions in graph: {G.number_of_nodes()}")
    print(f"Relationships: {G.number_of_edges()}")
    print(f"Communities detected: {len(communities)}")
    print(f"Modularity: {nx.community.modularity(G, communities):.4f}")

    for i, comm in enumerate(sorted(communities, key=len, reverse=True)):
        # Count factions in this community
        factions = {}
        for node in comm:
            f = G.nodes[node].get("faction", "Unknown")
            factions[f] = factions.get(f, 0) + 1
        top_faction = max(factions, key=factions.get)

        print(f"\n--- Community {i} ({len(comm)} members, dominant faction: {top_faction}) ---")
        # Sort members by faction
        members = sorted(comm, key=lambda n: G.nodes[n].get("faction", ""))
        for m in members:
            faction = G.nodes[m].get("faction", "?")
            print(f"  {m:20s} [{faction}]")


def build_interactive_viz(G, partition, communities, output_path="templates/network.html"):
    """Create an interactive Pyvis visualization."""
    net = Network(
        height="100vh",
        width="100%",
        bgcolor="#1a1a2e",
        font_color="white",
        select_menu=False,
        filter_menu=False,
    )

    net.barnes_hut(
        gravity=-3000,
        central_gravity=0.3,
        spring_length=150,
        spring_strength=0.01,
        damping=0.09,
    )

    # Add nodes colored by community
    for node in G.nodes:
        comm_id = partition.get(node, 0)
        color = COMMUNITY_COLORS[comm_id % len(COMMUNITY_COLORS)]
        faction = G.nodes[node].get("faction", "Unknown")
        role = G.nodes[node].get("role", "Unknown")
        degree = G.degree(node)

        title = (
            f"<b>{node}</b><br>"
            f"Faction: {faction}<br>"
            f"Role: {role}<br>"
            f"Community: {comm_id}<br>"
            f"Connections: {degree}"
        )

        net.add_node(
            node,
            label=node,
            title=title,
            color=color,
            size=10 + degree * 3,
            font={"size": 12, "color": "white", "strokeWidth": 2, "strokeColor": "#000"},
        )

    # Add edges
    for u, v, data in G.edges(data=True):
        relation = data.get("relation", "related")
        if relation == "rival":
            edge_color = "#ff4444"
            dash = True
        elif relation == "friend":
            edge_color = "#44ff44"
            dash = False
        else:
            edge_color = "#666666"
            dash = False

        net.add_edge(
            u, v,
            color=edge_color,
            title=relation,
            dashes=dash,
            width=1,
        )

    # Generate HTML
    net.set_options("""
    {
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "navigationButtons": true
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -3000,
          "centralGravity": 0.3,
          "springLength": 150,
          "springConstant": 0.01,
          "damping": 0.09
        },
        "stabilization": {
          "iterations": 200
        }
      }
    }
    """)

    # Generate the raw HTML from pyvis
    html_content = net.generate_html()

    # Wrap it in a nicer page with legend and controls
    legend_items = []
    for i, comm in enumerate(sorted(communities, key=len, reverse=True)):
        color = COMMUNITY_COLORS[i % len(COMMUNITY_COLORS)]
        factions = {}
        for node in comm:
            f = G.nodes[node].get("faction", "Unknown")
            factions[f] = factions.get(f, 0) + 1
        top_faction = max(factions, key=factions.get)
        legend_items.append(
            f'<span style="color:{color}; margin-right:15px;">&#9679; Community {i} ({len(comm)} champs, {top_faction})</span>'
        )

    legend_html = " ".join(legend_items)

    # Extract the body content from pyvis HTML and embed in our template
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>LoL Champion Relationship Network</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #1a1a2e; color: #eee; font-family: 'Segoe UI', sans-serif; }}
        .header {{
            padding: 15px 25px;
            background: #16213e;
            border-bottom: 2px solid #0f3460;
        }}
        .header h1 {{ font-size: 1.4em; color: #e94560; }}
        .header p {{ font-size: 0.85em; color: #aaa; margin-top: 4px; }}
        .legend {{
            padding: 10px 25px;
            background: #16213e;
            border-bottom: 1px solid #0f3460;
            font-size: 0.75em;
            line-height: 1.8;
            overflow-x: auto;
            white-space: nowrap;
        }}
        .edge-legend {{
            padding: 6px 25px;
            background: #16213e;
            border-bottom: 1px solid #0f3460;
            font-size: 0.75em;
        }}
        .edge-legend span {{ margin-right: 20px; }}
        .stats {{
            padding: 8px 25px;
            background: #0f3460;
            font-size: 0.8em;
        }}
        .stats span {{ margin-right: 25px; }}
        #graph-container {{ width: 100%; height: calc(100vh - 160px); }}
        iframe {{ border: none; width: 100%; height: 100%; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>League of Legends Champion Relationship Network</h1>
        <p>Interactive network graph with Louvain community detection. Hover over nodes for details. Drag to rearrange.</p>
    </div>
    <div class="stats">
        <span>Champions: {G.number_of_nodes()}</span>
        <span>Relationships: {G.number_of_edges()}</span>
        <span>Communities: {len(communities)}</span>
        <span>Modularity: {nx.community.modularity(G, communities):.4f}</span>
    </div>
    <div class="edge-legend">
        <span style="color:#44ff44;">&#9644; Friend</span>
        <span style="color:#ff4444;">- - Rival</span>
        <span style="color:#666;">&#9644; Related</span>
    </div>
    <div class="legend">{legend_html}</div>
    <div id="graph-container">
        <iframe src="graph_raw.html"></iframe>
    </div>
</body>
</html>"""

    # Write the raw pyvis graph
    raw_path = output_path.replace("network.html", "graph_raw.html")
    with open(raw_path, "w") as f:
        f.write(html_content)

    # Write the wrapper page
    with open(output_path, "w") as f:
        f.write(full_html)

    print(f"\nVisualization saved to {output_path}")
    print(f"Raw graph saved to {raw_path}")


def main():
    champions_new = load_data_new()
    champions_old = load_data_old()

    G = build_graph(champions_new, champions_old)
    partition, communities = detect_communities(G)
    print_community_report(G, partition, communities)
    build_interactive_viz(G, partition, communities)


if __name__ == "__main__":
    main()
