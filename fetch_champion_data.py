"""Stage and review a League Universe refresh before applying it to the graph.

Run ``python fetch_champion_data.py`` to fetch and write data_refresh/ for review.
Run ``python fetch_champion_data.py --apply-reviewed --rebuild-graph`` after
reviewing the manifest and CSV. The older friend/rival file is never changed.
"""

import argparse
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from champion_normalization import normalize_name_key


ROOT = Path(__file__).resolve().parent
REVIEW_DIR = ROOT / "data_refresh"
CANONICAL = ROOT / "champions_canonical.json"
UPDATED = ROOT / "champions_updated.json"
VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
ROSTER_URL = "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
BROWSE_URL = "https://universe-meeps.leagueoflegends.com/v1/en_us/champion-browse/index.json"
CHAMPION_URL = "https://universe-meeps.leagueoflegends.com/v1/en_us/champions/{slug}/index.json"
PAGE_URL = "https://universe.leagueoflegends.com/en_US/champion/{slug}/"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://universe.leagueoflegends.com/"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_json(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=20) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (TimeoutError, URLError):
            if attempt == 2:
                raise
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not fetch {url}")


def first_list_value(entry, field):
    values = entry.get(field, [])
    return values[0] if values else ""


def region_name(slug):
    if not slug:
        raise ValueError("missing region slug")
    return {"unaffiliated": "Runeterra", "void": "The Void", "mount-targon": "Targon"}.get(
        slug, slug.replace("-", " ").title()
    )


def parse_champion(name, slug, payload, roster_by_slug, fetched_at):
    champion = payload.get("champion")
    if not isinstance(champion, dict):
        raise ValueError("missing champion object")
    if normalize_name_key(champion.get("name")) != normalize_name_key(name) or champion.get("slug") != slug:
        raise ValueError(f"identity mismatch: {champion.get('name')} / {champion.get('slug')}")

    roles = champion.get("roles") or champion.get("role") or []
    if not isinstance(roles, list) or not roles:
        raise ValueError("missing roles")
    roles = [item.get("name", "").strip() for item in roles if isinstance(item, dict)]
    if not roles or any(not role for role in roles):
        raise ValueError("invalid roles")

    related_items = payload.get("related-champions")
    if not isinstance(related_items, list):
        raise ValueError("missing related-champions field")
    related = []
    for item in related_items:
        related_slug = item.get("slug") if isinstance(item, dict) else None
        target = roster_by_slug.get(related_slug)
        if not target:
            raise ValueError(f"unresolved related champion: {related_slug!r}")
        if target == name:
            raise ValueError("self relationship")
        if target not in related:
            related.append(target)

    races = champion.get("races") or []
    race = next((item.get("name", "") for item in races if isinstance(item, dict)), "")
    region_slug = champion.get("associated-faction-slug")
    return {
        "champion_name": [name],
        "region": [region_name(region_slug)],
        "related": related,
        "race": [race],
        "role": roles,
        "_source": {
            "verified": True,
            "page": PAGE_URL.format(slug=slug),
            "api": CHAMPION_URL.format(slug=slug),
            "fetched_at": fetched_at,
            "region_slug": region_slug,
            "related_status": "verified_empty" if not related else "verified",
        },
    }


def roster_with_slugs():
    version = fetch_json(VERSIONS_URL)[0]
    game_roster = fetch_json(ROSTER_URL.format(version=version))["data"]
    universe = fetch_json(BROWSE_URL)["champions"]
    game_by_key = {normalize_name_key(item["name"]): item["name"] for item in game_roster.values()}
    universe_keys = set()
    slugs = {}
    for item in universe:
        key = normalize_name_key(item.get("name"))
        if key in universe_keys:
            raise ValueError(f"duplicate Universe name: {item.get('name')}")
        universe_keys.add(key)
        name = game_by_key.get(key, item["name"])
        slug = item["slug"]
        if slug in slugs:
            raise ValueError(f"Duplicate slug {slug}")
        slugs[slug] = name
    missing_from_universe = set(game_by_key) - universe_keys
    if missing_from_universe:
        raise ValueError(f"Game champions missing from League Universe: {sorted(game_by_key[key] for key in missing_from_universe)}")
    universe_only = sorted(name for name in slugs.values() if normalize_name_key(name) not in game_by_key)
    return version, slugs, len(game_roster), universe_only


def changes_for(old_entries, new_entries):
    before = {normalize_name_key(first_list_value(entry, "champion_name")): entry for entry in old_entries}
    changes = []
    for entry in new_entries:
        name = first_list_value(entry, "champion_name")
        prior = before.get(normalize_name_key(name), {})
        for field in ("region", "role", "related", "race"):
            old = prior.get(field, [])
            new = entry[field]
            if field == "related":
                differs = set(filter(None, old)) != set(new)
            else:
                differs = old != new
            if differs:
                changes.append({
                    "champion": name, "field": field,
                    "old": json.dumps(old, ensure_ascii=False),
                    "new": json.dumps(new, ensure_ascii=False),
                    "source": entry["_source"]["page"],
                })
    return changes


def stage_refresh():
    version, roster_by_slug, game_roster_count, universe_only = roster_with_slugs()
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entries, issues = [], []
    for index, (slug, name) in enumerate(sorted(roster_by_slug.items(), key=lambda pair: pair[1])):
        try:
            entries.append(parse_champion(name, slug, fetch_json(CHAMPION_URL.format(slug=slug)), roster_by_slug, fetched_at))
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError) as error:
            issues.append({"champion": name, "slug": slug, "error": str(error)})
        if (index + 1) % 25 == 0:
            print(f"Fetched {index + 1}/{len(roster_by_slug)} champions", flush=True)
        time.sleep(0.12)

    REVIEW_DIR.mkdir(exist_ok=True)
    review = REVIEW_DIR / "champions_review.json"
    report = REVIEW_DIR / "changes.csv"
    write_json(review, entries)
    changes = changes_for(read_json(CANONICAL), entries)
    with report.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=("champion", "field", "old", "new", "source"))
        writer.writeheader()
        writer.writerows(changes)
    manifest = {
        "fetched_at": fetched_at,
        "game_version": version,
        "game_roster_count": game_roster_count,
        "universe_only": universe_only,
        "roster_count": len(roster_by_slug),
        "verified_count": len(entries),
        "change_count": len(changes),
        "baseline_sha256": digest(CANONICAL),
        "review_sha256": digest(review),
        "issues": issues,
    }
    write_json(REVIEW_DIR / "manifest.json", manifest)
    print(f"Staged {len(entries)}/{len(roster_by_slug)} champions; {len(changes)} field changes; {len(issues)} issues")
    return manifest


def apply_reviewed(rebuild_graph):
    manifest = read_json(REVIEW_DIR / "manifest.json")
    review = REVIEW_DIR / "champions_review.json"
    if manifest["issues"] or manifest["verified_count"] != manifest["roster_count"]:
        raise ValueError("Review has unresolved fetch or validation issues")
    if digest(CANONICAL) != manifest["baseline_sha256"]:
        raise ValueError("Canonical data changed after staging; refresh the review")
    if digest(review) != manifest["review_sha256"]:
        raise ValueError("Reviewed data changed after staging; refresh the review")
    entries = read_json(review)
    if len(entries) != manifest["roster_count"] or not all(e.get("_source", {}).get("verified") for e in entries):
        raise ValueError("Review is incomplete")
    write_json(UPDATED, entries)
    write_json(CANONICAL, entries)
    fetched_date = datetime.fromisoformat(manifest["fetched_at"])
    date = f"{fetched_date:%B} {fetched_date.day}, {fetched_date.year}"
    write_json(ROOT / "data_snapshot.json", {
        "label": f"League Universe snapshot: {date}",
        "note": f"Universe champion pages and Riot Data Dragon roster {manifest['game_version']}; fetched {manifest['fetched_at']}.",
    })
    if rebuild_graph:
        import community_analysis
        community_analysis.main()
    print(f"Applied {len(entries)} verified champions")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-reviewed", action="store_true", help="Apply an issue-free staged refresh")
    parser.add_argument("--rebuild-graph", action="store_true", help="Regenerate the HTML and portable demo after applying")
    args = parser.parse_args()
    if args.rebuild_graph and not args.apply_reviewed:
        parser.error("--rebuild-graph requires --apply-reviewed")
    if args.apply_reviewed:
        apply_reviewed(args.rebuild_graph)
    else:
        stage_refresh()


if __name__ == "__main__":
    main()
