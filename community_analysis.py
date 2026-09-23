"""
Community detection and interactive visualization for League of Legends champion relationships.
Uses NetworkX for graph analysis (Louvain community detection) and Pyvis for interactive visualization.
"""

import json
import os

try:
    import numpy as np
except ImportError:
    np = None
else:
    # Older NetworkX versions in the checked-in virtualenv still reference
    # NumPy aliases removed in NumPy 2.x.
    if not hasattr(np, "float_"):
        np.float_ = np.float64
    if not hasattr(np, "int"):
        np.int = int
    if not hasattr(np, "float"):
        np.float = float
    if not hasattr(np, "complex"):
        np.complex = complex

import networkx as nx

from champion_normalization import normalize_champion_name, normalize_name_key

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

def first_value(entry, field):
    values = entry.get(field, [""])
    if not values:
        return ""
    return values[0]


def load_data_new(path="champions_canonical.json", fallback_path="champions_new.json"):
    """Load the newer dataset which has region/related/race/role fields."""
    with open(path) as f:
        data = json.load(f)

    fallback_by_key = {}
    canonical_names = {}
    if fallback_path and os.path.exists(fallback_path):
        with open(fallback_path) as f:
            fallback_data = json.load(f)
        for entry in fallback_data:
            name = first_value(entry, "champion_name")
            normalized = normalize_champion_name(name)
            key = normalize_name_key(normalized)
            canonical_names[key] = normalized
            fallback_by_key[key] = entry

    for entry in data:
        name = first_value(entry, "champion_name")
        normalized = normalize_champion_name(name)
        canonical_names[normalize_name_key(normalized)] = normalized

    champions = {}
    for entry in data:
        name = normalize_champion_name(first_value(entry, "champion_name"), canonical_names)
        key = normalize_name_key(name)
        fallback = fallback_by_key.get(key, {})
        region = first_value(entry, "region")
        fallback_region = first_value(fallback, "region")
        if not region or (not entry.get("_source", {}).get("verified") and region == "Runeterra" and fallback_region and fallback_region != "Runeterra"):
            region = fallback_region
        race = first_value(entry, "race") or first_value(fallback, "race")
        roles = [value for value in entry.get("role", []) if value]
        role = " / ".join(roles) if roles else first_value(fallback, "role")
        champions[name] = {
            "region": region,
            "related": [
                normalize_champion_name(r, canonical_names)
                for r in entry.get("related", [""])
                if normalize_champion_name(r, canonical_names)
            ],
            "race": race,
            "role": role,
            "url": entry.get("_source", {}).get("page", ""),
        }
    return champions


def load_data_old(path="champions.json"):
    """Load the older dataset which has friends/rivals/faction fields."""
    with open(path) as f:
        data = json.load(f)

    champions = {}
    for entry in data:
        name = normalize_champion_name(entry["champion_name"][0])
        champions[name] = {
            "faction": entry.get("faction", [""])[0],
            "friends": [normalize_champion_name(r) for r in entry.get("friends", [""]) if r],
            "rivals": [normalize_champion_name(r) for r in entry.get("rivals", [""]) if r],
        }
    return champions


def build_graph(champions_new, champions_old):
    """Combine relationship evidence before assigning an undirected edge type."""
    G = nx.Graph()
    node_lookup = {normalize_name_key(name): name for name in champions_new}

    # Add all champions as nodes with attributes
    for name, data in champions_new.items():
        faction = data["region"]
        # Try to get faction from old data if available
        old_data = champions_old.get(name)

        old_faction = old_data["faction"] if old_data else ""
        display_faction = faction if faction else old_faction

        G.add_node(name, faction=display_faction, role=data["role"], race=data["race"], url=data.get("url", ""))

    evidence = {}

    def record(source, target, label):
        target = node_lookup.get(normalize_name_key(target))
        if target and target != source:
            pair = tuple(sorted((source, target)))
            evidence.setdefault(pair, set()).add(label)

    # Related means a connection is listed; it does not imply friendship.
    for name, data in champions_new.items():
        for related in data["related"]:
            record(name, related, "related")

    # Add edges from old dataset (friends and rivals)
    for old_name, data in champions_old.items():
        # Find matching node in graph
        match = node_lookup.get(normalize_name_key(old_name))
        if not match:
            continue

        for friend in data.get("friends", []):
            record(match, friend, "friend")

        for rival in data.get("rivals", []):
            record(match, rival, "rival")

    for (source, target), labels in sorted(evidence.items()):
        if "friend" in labels and "rival" in labels:
            relation = "mixed"
        elif "friend" in labels:
            relation = "friend"
        elif "rival" in labels:
            relation = "rival"
        else:
            relation = "related"
        G.add_edge(source, target, relation=relation, evidence=sorted(labels))

    return G


def detect_communities(G):
    """Run Louvain community detection."""
    isolates = list(nx.isolates(G))
    graph_for_detection = G.copy()
    graph_for_detection.remove_nodes_from(isolates)

    if graph_for_detection.number_of_nodes() == 0:
        communities = []
    elif hasattr(nx.community, "louvain_communities"):
        communities = nx.community.louvain_communities(graph_for_detection, seed=42)
    else:
        communities = list(nx.community.greedy_modularity_communities(graph_for_detection))

    communities = [set(comm) for comm in communities]
    for node in isolates:
        communities.append({node})

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
    modularity = 0 if G.number_of_edges() == 0 else nx.community.modularity(G, communities)
    print(f"Modularity: {modularity:.4f}")

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
        "Ambessa": "ambessa",
        "Akshan": "akshan",
        "Bel'Veth": "belveth",
        "Nunu & Willump": "nunu",
        "Dr. Mundo": "drmundo",
        "Cho'Gath": "chogath",
        "Hwei": "hwei",
        "K'Sante": "ksante",
        "Kha'Zix": "khazix",
        "Kog'Maw": "kogmaw",
        "Rek'Sai": "reksai",
        "Vel'Koz": "velkoz",
        "Kai'Sa": "kaisa",
        "Xin Zhao": "xinzhao",
        "Jarvan IV": "jarvaniv",
        "Lee Sin": "leesin",
        "Mel": "mel",
        "Miss Fortune": "missfortune",
        "Master Yi": "masteryi",
        "Nilah": "nilah",
        "Renata Glasc": "renataglasc",
        "Smolder": "smolder",
        "Twisted Fate": "twistedfate",
        "Tahm Kench": "tahmkench",
        "Aurelion Sol": "aurelionsol",
        "LeBlanc": "leblanc",
        "Viego": "viego",
    }
    if name in special:
        return special[name] + ".png"
    return name.lower().replace(" ", "").replace("'", "") + ".png"


IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "R_analysis", "img")



def main():
    champions_new = load_data_new()
    champions_old = load_data_old()

    G = build_graph(champions_new, champions_old)
    partition, communities = detect_communities(G)
    print_community_report(G, partition, communities)
    from portfolio_render import build_portfolio
    build_portfolio(G, partition, champion_to_image_filename)


if __name__ == "__main__":
    main()
