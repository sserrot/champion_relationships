"""
Community detection and interactive visualization for League of Legends champion relationships.
Uses NetworkX for graph analysis (Louvain community detection) and Pyvis for interactive visualization.
"""

import json
import os
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


def champion_to_image_filename(name):
    """Convert a champion display name to its image filename."""
    # Special cases mapping
    special = {
        "Nunu & Willump": "nunu",
        "Dr. Mundo": "drmundo",
        "Cho'Gath": "chogath",
        "Kha'Zix": "khazix",
        "Kog'Maw": "kogmaw",
        "Rek'Sai": "reksai",
        "Vel'Koz": "velkoz",
        "Kai'sa": "kaisa",
        "Xin Zhao": "xinzhao",
        "Jarvan IV": "jarvaniv",
        "Lee Sin": "leesin",
        "Miss Fortune": "missfortune",
        "Master Yi": "masteryi",
        "Twisted Fate": "twistedfate",
        "Tahm Kench": "tahmkench",
        "Aurelion Sol": "aurelionsol",
        "LeBlanc": "leblanc",
    }
    if name in special:
        return special[name] + ".png"
    return name.lower().replace(" ", "").replace("'", "") + ".png"


IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "R_analysis", "img")


def build_interactive_viz(G, partition, communities, output_path="templates/network.html"):
    """Create an interactive visualization with filter controls, embedded directly (no iframe)."""

    # Build node and edge data as JSON for vis.js
    nodes_data = []
    for node in G.nodes:
        comm_id = partition.get(node, 0)
        color = COMMUNITY_COLORS[comm_id % len(COMMUNITY_COLORS)]
        faction = G.nodes[node].get("faction", "Unknown")
        role = G.nodes[node].get("role", "Unknown")
        degree = G.degree(node)

        img_file = champion_to_image_filename(node)
        img_path = os.path.join(IMG_DIR, img_file)
        has_image = os.path.exists(img_path)

        node_obj = {
            "id": node,
            "label": node,
            "faction": faction,
            "role": role,
            "community": comm_id,
            "degree": degree,
            "font": {"size": 10, "color": "white", "strokeWidth": 2, "strokeColor": "#000"},
        }

        if has_image:
            node_obj.update({
                "shape": "circularImage",
                "image": f"/img/{img_file}",
                "size": 25 + degree * 2,
                "borderWidth": 3,
                "color": {"border": color, "highlight": {"border": "#ffffff"}},
            })
        else:
            node_obj.update({
                "shape": "dot",
                "size": 10 + degree * 3,
                "color": color,
            })

        nodes_data.append(node_obj)

    edges_data = []
    for u, v, data in G.edges(data=True):
        relation = data.get("relation", "related")
        edge_obj = {"from": u, "to": v, "relation": relation, "width": 1}
        if relation == "rival":
            edge_obj["color"] = "#ff4444"
            edge_obj["dashes"] = True
        elif relation == "friend":
            edge_obj["color"] = "#44ff44"
            edge_obj["dashes"] = False
        else:
            edge_obj["color"] = "#666666"
            edge_obj["dashes"] = False
        edges_data.append(edge_obj)

    nodes_json = json.dumps(nodes_data)
    edges_json = json.dumps(edges_data)

    # Build legend
    legend_items = []
    sorted_comms = sorted(enumerate(communities), key=lambda x: len(x[1]), reverse=True)
    for display_idx, (orig_idx, comm) in enumerate(sorted_comms):
        color = COMMUNITY_COLORS[orig_idx % len(COMMUNITY_COLORS)]
        factions = {}
        for node in comm:
            f = G.nodes[node].get("faction", "Unknown")
            factions[f] = factions.get(f, 0) + 1
        top_faction = max(factions, key=factions.get)
        legend_items.append(
            f'<span style="color:{color}; margin-right:15px;">&#9679; Community {orig_idx} ({len(comm)}, {top_faction})</span>'
        )
    legend_html = " ".join(legend_items)

    # Get sorted champion list and faction list for filters
    all_champions = sorted(G.nodes)
    all_factions = sorted(set(G.nodes[n].get("faction", "") for n in G.nodes) - {""})
    community_ids = sorted(set(partition.values()))

    champ_options = "".join(f'<option value="{c}">{c}</option>' for c in all_champions)
    faction_options = "".join(f'<option value="{f}">{f}</option>' for f in all_factions)
    community_options = "".join(f'<option value="{c}">Community {c}</option>' for c in community_ids)

    modularity = nx.community.modularity(G, communities)

    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>LoL Champion Relationship Network</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #1a1a2e; color: #eee; font-family: 'Segoe UI', sans-serif; }}
        .header {{
            padding: 12px 25px;
            background: #16213e;
            border-bottom: 2px solid #0f3460;
        }}
        .header h1 {{ font-size: 1.4em; color: #e94560; display: inline; }}
        .header p {{ font-size: 0.85em; color: #aaa; margin-top: 4px; }}
        .controls {{
            padding: 10px 25px;
            background: #16213e;
            border-bottom: 1px solid #0f3460;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .controls label {{ font-size: 0.8em; color: #aaa; }}
        .controls select, .controls input {{
            background: #1a1a2e;
            color: #eee;
            border: 1px solid #0f3460;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
        }}
        .controls select {{ max-width: 180px; }}
        .controls select[multiple] {{ height: 28px; }}
        .controls button {{
            background: #e94560;
            color: white;
            border: none;
            padding: 5px 14px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8em;
        }}
        .controls button:hover {{ background: #c73a52; }}
        .controls button.secondary {{
            background: #0f3460;
        }}
        .controls button.secondary:hover {{ background: #1a4a8a; }}
        .filter-group {{
            display: flex;
            flex-direction: column;
            gap: 3px;
        }}
        .hidden-chips {{
            padding: 4px 25px;
            background: #0d1b2a;
            font-size: 0.75em;
            display: none;
            flex-wrap: wrap;
            gap: 5px;
            align-items: center;
        }}
        .hidden-chips.active {{ display: flex; }}
        .chip {{
            background: #e94560;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }}
        .chip:hover {{ background: #c73a52; }}
        .chip .x {{ font-weight: bold; }}
        .legend {{
            padding: 6px 25px;
            background: #16213e;
            border-bottom: 1px solid #0f3460;
            font-size: 0.7em;
            line-height: 1.8;
            overflow-x: auto;
            white-space: nowrap;
        }}
        .edge-legend {{
            padding: 4px 25px;
            background: #16213e;
            border-bottom: 1px solid #0f3460;
            font-size: 0.75em;
        }}
        .edge-legend span {{ margin-right: 20px; }}
        .stats {{
            padding: 6px 25px;
            background: #0f3460;
            font-size: 0.8em;
        }}
        .stats span {{ margin-right: 25px; }}
        #network {{
            width: 100%;
            height: calc(100vh - 220px);
            background: #1a1a2e;
        }}
        div.vis-tooltip {{
            background-color: #16213e !important;
            color: #eee !important;
            border: 1px solid #0f3460 !important;
            border-radius: 6px !important;
            padding: 8px 12px !important;
            font-family: 'Segoe UI', sans-serif !important;
            font-size: 13px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.5) !important;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>League of Legends Champion Relationship Network</h1>
        <p>Interactive network with Louvain community detection. Hover for details. Drag to rearrange. Use filters to hide champions.</p>
    </div>
    <div class="controls">
        <div class="filter-group">
            <label>Hide champion:</label>
            <select id="champ-select">
                <option value="">-- Select --</option>
                {champ_options}
            </select>
        </div>
        <div class="filter-group">
            <label>Hide faction:</label>
            <select id="faction-select">
                <option value="">-- Select --</option>
                {faction_options}
            </select>
        </div>
        <div class="filter-group">
            <label>Hide community:</label>
            <select id="community-select">
                <option value="">-- Select --</option>
                {community_options}
            </select>
        </div>
        <div class="filter-group">
            <label>Show only:</label>
            <select id="show-relation">
                <option value="all">All edges</option>
                <option value="friend">Friends only</option>
                <option value="rival">Rivals only</option>
                <option value="related">Related only</option>
            </select>
        </div>
        <div class="filter-group">
            <label>&nbsp;</label>
            <button class="secondary" onclick="resetFilters()">Reset All</button>
        </div>
    </div>
    <div class="hidden-chips" id="hidden-chips">
        <span style="color:#aaa;">Hidden:</span>
    </div>
    <div class="stats" id="stats-bar">
        <span>Champions: {G.number_of_nodes()}</span>
        <span>Relationships: {G.number_of_edges()}</span>
        <span>Communities: {len(communities)}</span>
        <span>Modularity: {modularity:.4f}</span>
    </div>
    <div class="edge-legend">
        <span style="color:#44ff44;">&#9644; Friend</span>
        <span style="color:#ff4444;">- - Rival</span>
        <span style="color:#666;">&#9644; Related</span>
    </div>
    <div class="legend">{legend_html}</div>
    <div id="network"></div>

    <script>
        // Full graph data
        var allNodes = {nodes_json};
        var allEdges = {edges_json};

        // Track hidden items
        var hiddenChampions = new Set();
        var hiddenFactions = new Set();
        var hiddenCommunities = new Set();
        var edgeFilter = "all";

        // Create vis DataSets
        var nodesDataset = new vis.DataSet(allNodes);
        var edgesDataset = new vis.DataSet(allEdges);

        // Create network
        var container = document.getElementById("network");
        var data = {{ nodes: nodesDataset, edges: edgesDataset }};
        var options = {{
            interaction: {{
                hover: true,
                tooltipDelay: 100,
                navigationButtons: true
            }},
            physics: {{
                barnesHut: {{
                    gravitationalConstant: -3000,
                    centralGravity: 0.3,
                    springLength: 150,
                    springConstant: 0.01,
                    damping: 0.09
                }},
                stabilization: {{
                    iterations: 200
                }}
            }}
        }};

        var network = new vis.Network(container, data, options);

        // Build tooltip content
        function makeTitle(n) {{
            return "<b>" + n.id + "</b><br>" +
                   "Faction: " + n.faction + "<br>" +
                   "Role: " + n.role + "<br>" +
                   "Community: " + n.community + "<br>" +
                   "Connections: " + n.degree;
        }}
        // Set initial tooltips
        allNodes.forEach(function(n) {{
            nodesDataset.update({{ id: n.id, title: makeTitle(n) }});
        }});

        function applyFilters() {{
            // Determine which nodes to show
            var visibleNodeIds = new Set();
            allNodes.forEach(function(n) {{
                if (hiddenChampions.has(n.id)) return;
                if (hiddenFactions.has(n.faction)) return;
                if (hiddenCommunities.has(n.community)) return;
                visibleNodeIds.add(n.id);
            }});

            // Update nodes dataset
            var currentNodeIds = nodesDataset.getIds();
            // Remove nodes that should be hidden
            var toRemove = currentNodeIds.filter(function(id) {{ return !visibleNodeIds.has(id); }});
            nodesDataset.remove(toRemove);
            // Add nodes that should be visible
            allNodes.forEach(function(n) {{
                if (visibleNodeIds.has(n.id) && !nodesDataset.get(n.id)) {{
                    var nodeWithTitle = Object.assign({{}}, n, {{ title: makeTitle(n) }});
                    nodesDataset.add(nodeWithTitle);
                }}
            }});

            // Update edges dataset
            var currentEdgeIds = edgesDataset.getIds();
            edgesDataset.remove(currentEdgeIds);
            allEdges.forEach(function(e, idx) {{
                if (!visibleNodeIds.has(e.from) || !visibleNodeIds.has(e.to)) return;
                if (edgeFilter !== "all" && e.relation !== edgeFilter) return;
                var edge = Object.assign({{}}, e, {{ id: idx }});
                edgesDataset.add(edge);
            }});

            // Update stats
            var nodeCount = visibleNodeIds.size;
            var edgeCount = edgesDataset.length;
            document.getElementById("stats-bar").innerHTML =
                "<span>Champions: " + nodeCount + " / {G.number_of_nodes()}</span>" +
                "<span>Relationships: " + edgeCount + " / {G.number_of_edges()}</span>" +
                "<span>Communities: {len(communities)}</span>" +
                "<span>Modularity: {modularity:.4f}</span>";

            // Update chips
            updateChips();
        }}

        function updateChips() {{
            var container = document.getElementById("hidden-chips");
            var chips = '<span style="color:#aaa;">Hidden:</span>';
            var hasAny = false;

            hiddenChampions.forEach(function(c) {{
                hasAny = true;
                chips += ' <span class="chip" onclick="unhideChampion(\\''+c+'\\')">'+c+' <span class="x">&times;</span></span>';
            }});
            hiddenFactions.forEach(function(f) {{
                hasAny = true;
                chips += ' <span class="chip" onclick="unhideFaction(\\''+f+'\\')">'+f+' (faction) <span class="x">&times;</span></span>';
            }});
            hiddenCommunities.forEach(function(c) {{
                hasAny = true;
                chips += ' <span class="chip" onclick="unhideCommunity('+c+')">Community '+c+' <span class="x">&times;</span></span>';
            }});

            container.innerHTML = chips;
            container.className = hasAny ? "hidden-chips active" : "hidden-chips";
        }}

        // Hide handlers
        document.getElementById("champ-select").addEventListener("change", function() {{
            if (this.value) {{
                hiddenChampions.add(this.value);
                this.value = "";
                applyFilters();
            }}
        }});
        document.getElementById("faction-select").addEventListener("change", function() {{
            if (this.value) {{
                hiddenFactions.add(this.value);
                this.value = "";
                applyFilters();
            }}
        }});
        document.getElementById("community-select").addEventListener("change", function() {{
            if (this.value !== "") {{
                hiddenCommunities.add(parseInt(this.value));
                this.value = "";
                applyFilters();
            }}
        }});
        document.getElementById("show-relation").addEventListener("change", function() {{
            edgeFilter = this.value;
            applyFilters();
        }});

        // Unhide handlers
        function unhideChampion(c) {{ hiddenChampions.delete(c); applyFilters(); }}
        function unhideFaction(f) {{ hiddenFactions.delete(f); applyFilters(); }}
        function unhideCommunity(c) {{ hiddenCommunities.delete(c); applyFilters(); }}

        function resetFilters() {{
            hiddenChampions.clear();
            hiddenFactions.clear();
            hiddenCommunities.clear();
            edgeFilter = "all";
            document.getElementById("show-relation").value = "all";
            applyFilters();
        }}
    </script>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(full_html)

    print(f"\nVisualization saved to {output_path}")


def main():
    champions_new = load_data_new()
    champions_old = load_data_old()

    G = build_graph(champions_new, champions_old)
    partition, communities = detect_communities(G)
    print_community_report(G, partition, communities)
    build_interactive_viz(G, partition, communities)


if __name__ == "__main__":
    main()
