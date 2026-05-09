"""
Fetch League of Legends champion lore data (related champions, region, race, role).

Strategy:
  1. Primary: Hit the undocumented universe-meeps JSON API endpoints
  2. Fallback: Scrape the Universe site using requests + BeautifulSoup
  3. Last resort: Use Playwright (headless browser) for JS-rendered content

Usage:
  pip install requests beautifulsoup4 lxml
  python fetch_champion_data.py
  python fetch_champion_data.py --rebuild-graph

Optional (for fallback headless scraping):
  pip install playwright && playwright install chromium
"""

import argparse
import json
import re
import sys
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

DDRAGON_VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
DDRAGON_CHAMPIONS_URL = "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
MEEPS_CHAMPION_URL = "https://universe-meeps.leagueoflegends.com/v1/en_us/champion/{slug}/index.json"
MEEPS_BROWSE_URL = "https://universe-meeps.leagueoflegends.com/v1/en_us/champion-browse/index.json"
UNIVERSE_CHAMPION_URL = "https://universe.leagueoflegends.com/en_us/champion/{slug}/"

OUTPUT_FILE = "champions_updated.json"


def load_existing() -> dict[str, dict]:
    """Load already-fetched champions from the output file, keyed by name."""
    path = Path(OUTPUT_FILE)
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        existing = {}
        for entry in data:
            name = entry["champion_name"][0]
            existing[name] = entry
        return existing
    except (json.JSONDecodeError, KeyError, IndexError):
        return {}


def save_results(existing: dict[str, dict]):
    """Save the combined results dict, sorted by name."""
    results = sorted(existing.values(), key=lambda x: x["champion_name"][0])
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    total = len(results)
    with_rel = sum(1 for r in results if r["related"] != [""])
    log.info(f"Saved {total} champions to {OUTPUT_FILE} ({with_rel} with relationships)")
    return total


def run_canonical_pipeline(rebuild_graph: bool = False):
    """Merge fetched data into the canonical dataset, optionally rebuilding HTML."""
    import merge_champion_data

    merge_champion_data.main()

    if rebuild_graph:
        import community_analysis

        community_analysis.main()


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Fetch champion relationship data, merge it into champions_canonical.json, "
            "and optionally rebuild the interactive network."
        )
    )
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="Skip network fetching and only rebuild champions_canonical.json from local JSON files.",
    )
    parser.add_argument(
        "--skip-merge",
        action="store_true",
        help="Only update champions_updated.json; do not refresh champions_canonical.json.",
    )
    parser.add_argument(
        "--rebuild-graph",
        action="store_true",
        help="After merging canonical data, regenerate templates/network.html.",
    )
    return parser.parse_args()

# Mapping of special champion name -> universe slug
SLUG_OVERRIDES = {
    "Wukong": "monkeyking",
    "Renata Glasc": "renata",
    "Nunu & Willump": "nunu",
}

SESSION = None


def require_requests():
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Install requests to fetch champion data: pip install requests") from exc
    return requests


def require_beautiful_soup():
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("Install Beautiful Soup to scrape champion data: pip install beautifulsoup4 lxml") from exc
    return BeautifulSoup


def get_session():
    global SESSION
    if SESSION is None:
        requests = require_requests()
        SESSION = requests.Session()
        SESSION.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://universe.leagueoflegends.com/",
            "Origin": "https://universe.leagueoflegends.com",
        })
    return SESSION


def get_champion_slugs() -> dict[str, str]:
    """Get champion name -> slug mapping from Data Dragon."""
    session = get_session()
    log.info("Fetching champion list from Data Dragon...")
    resp = session.get(DDRAGON_VERSIONS_URL, timeout=10)
    resp.raise_for_status()
    version = resp.json()[0]
    log.info(f"Latest game version: {version}")

    resp = session.get(DDRAGON_CHAMPIONS_URL.format(version=version), timeout=10)
    resp.raise_for_status()
    data = resp.json()["data"]

    slugs = {}
    for key, champ in data.items():
        name = champ["name"]
        # Universe URL slug: lowercase, no spaces/punctuation, some special cases
        slug = SLUG_OVERRIDES.get(name)
        if not slug:
            slug = re.sub(r"[^a-zA-Z]", "", name).lower()
        slugs[name] = slug

    log.info(f"Found {len(slugs)} champions")
    return slugs


# ---------------------------------------------------------------------------
# Strategy 1: Universe Meeps JSON API
# ---------------------------------------------------------------------------

def fetch_via_meeps(slugs: dict[str, str], existing: dict[str, dict]) -> bool:
    """Try the undocumented universe-meeps API. Updates existing dict in-place."""
    requests = require_requests()
    session = get_session()
    log.info("Attempting universe-meeps API...")

    # Quick test with a single champion
    test_url = MEEPS_CHAMPION_URL.format(slug="aatrox")
    try:
        resp = session.get(test_url, timeout=10)
        if resp.status_code != 200:
            log.warning(f"Meeps API returned {resp.status_code} — skipping this strategy")
            return False
    except requests.RequestException as e:
        log.warning(f"Meeps API unreachable: {e}")
        return False

    remaining = {n: s for n, s in slugs.items() if n not in existing}
    log.info(f"Meeps API accessible! {len(remaining)} champions remaining (skipping {len(existing)} already fetched)")
    if not remaining:
        return True

    fetched = 0
    for name, slug in remaining.items():
        url = MEEPS_CHAMPION_URL.format(slug=slug)
        try:
            resp = session.get(url, timeout=10)
            if resp.status_code != 200:
                log.warning(f"  {name} ({slug}): HTTP {resp.status_code}")
                continue

            data = resp.json()
            champion_data = data.get("champion", data)

            # Extract related champions
            related = []
            for rel in champion_data.get("related-champions", []):
                rel_name = rel.get("name", rel.get("title", ""))
                if rel_name:
                    related.append(rel_name)

            # Extract faction/region
            region = ""
            faction = champion_data.get("associated-faction-slug", "")
            if faction:
                region = faction.replace("-", " ").title()
            elif "faction" in champion_data:
                f = champion_data["faction"]
                region = f.get("name", "") if isinstance(f, dict) else str(f)

            # Extract race
            race = ""
            for tag in champion_data.get("races", champion_data.get("race", [])):
                if isinstance(tag, dict):
                    race = tag.get("name", "")
                else:
                    race = str(tag)
                break

            # Extract role
            role = ""
            for r in champion_data.get("roles", champion_data.get("role", [])):
                if isinstance(r, dict):
                    role = r.get("name", "")
                else:
                    role = str(r)
                break

            existing[name] = {
                "champion_name": [name],
                "region": [region if region else "Runeterra"],
                "related": related if related else [""],
                "race": [race],
                "role": [role],
            }
            fetched += 1
            log.info(f"  {name}: {len(related)} related champions")

            # Save incrementally every 10 champions
            if fetched % 10 == 0:
                save_results(existing)
                log.info(f"  [checkpoint] {len(existing)}/{len(slugs)} total")

        except Exception as e:
            log.warning(f"  {name}: error — {e}")

        time.sleep(0.2)  # Rate limit

    # Final save
    if fetched > 0:
        save_results(existing)

    return fetched > 0 or len(existing) > 0


# ---------------------------------------------------------------------------
# Strategy 2: Scrape Universe HTML (works if server-side rendered)
# ---------------------------------------------------------------------------

def fetch_via_html_scrape(slugs: dict[str, str], existing: dict[str, dict]) -> bool:
    """Scrape the Universe champion pages directly. Updates existing dict in-place."""
    requests = require_requests()
    session = get_session()
    BeautifulSoup = require_beautiful_soup()
    log.info("Attempting HTML scrape of Universe site...")

    test_url = UNIVERSE_CHAMPION_URL.format(slug="aatrox")
    try:
        resp = session.get(test_url, timeout=15)
        if resp.status_code != 200:
            log.warning(f"Universe site returned {resp.status_code}")
            return False
        if "related" not in resp.text.lower() and "relatedChampions" not in resp.text:
            log.warning("Universe page appears to be JS-rendered only — HTML scrape won't work")
            return False
    except requests.RequestException as e:
        log.warning(f"Universe site unreachable: {e}")
        return False

    remaining = {n: s for n, s in slugs.items() if n not in existing}
    log.info(f"Universe site accessible! {len(remaining)} champions remaining (skipping {len(existing)} already fetched)")
    if not remaining:
        return True

    fetched = 0
    for name, slug in remaining.items():
        url = UNIVERSE_CHAMPION_URL.format(slug=slug)
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                log.warning(f"  {name}: HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            scripts = soup.find_all("script")
            champion_json = None
            for script in scripts:
                if script.string and ("related-champions" in script.string or "relatedChampions" in script.string):
                    match = re.search(r'(\{.*"champion".*\})', script.string, re.DOTALL)
                    if match:
                        try:
                            champion_json = json.loads(match.group(1))
                        except json.JSONDecodeError:
                            pass

            if champion_json:
                cdata = champion_json.get("champion", champion_json)
                related = [r.get("name", "") for r in cdata.get("related-champions", [])]
                region = cdata.get("associated-faction-slug", "").replace("-", " ").title() or "Runeterra"
                race = ""
                role = ""
            else:
                related = []
                related_section = soup.find("ul", class_=re.compile(r"relatedChampions|champion.*grid|shouldScroll"))
                if related_section:
                    for li in related_section.find_all("li"):
                        link = li.find("a")
                        if link and link.get("href", "").startswith("/en_us/champion/"):
                            champ_name_el = li.find("h6") or li.find("div", class_=re.compile(r"champ"))
                            if champ_name_el:
                                related.append(champ_name_el.get_text(strip=True))
                            else:
                                href_slug = link["href"].rstrip("/").split("/")[-1]
                                related.append(href_slug.title())

                region_el = soup.find("div", class_=re.compile(r"race_|region"))
                region = region_el.get_text(strip=True) if region_el else "Runeterra"

                race = ""
                race_el = soup.find("div", class_=re.compile(r"race_"))
                if race_el:
                    race = race_el.get_text(strip=True)

                role = ""
                role_el = soup.find(string=re.compile(r"^(Fighter|Mage|Assassin|Marksman|Tank|Support)$"))
                if role_el:
                    role = role_el.strip()

            existing[name] = {
                "champion_name": [name],
                "region": [region],
                "related": related if related else [""],
                "race": [race],
                "role": [role],
            }
            fetched += 1
            log.info(f"  {name}: {len(related)} related")

            if fetched % 10 == 0:
                save_results(existing)
                log.info(f"  [checkpoint] {len(existing)}/{len(slugs)} total")

        except Exception as e:
            log.warning(f"  {name}: error — {e}")

        time.sleep(0.3)

    if fetched > 0:
        save_results(existing)

    return fetched > 0 or len(existing) > 0


# ---------------------------------------------------------------------------
# Strategy 3: Playwright headless browser
# ---------------------------------------------------------------------------

def fetch_via_playwright(slugs: dict[str, str], existing: dict[str, dict]) -> bool:
    """Use Playwright to render JS and scrape the fully loaded page. Updates existing dict in-place."""
    BeautifulSoup = require_beautiful_soup()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.warning("Playwright not installed. Install with: pip install playwright && playwright install chromium")
        return False

    remaining = {n: s for n, s in slugs.items() if n not in existing}
    log.info(f"Using Playwright headless browser... {len(remaining)} champions remaining (skipping {len(existing)} already fetched)")
    if not remaining:
        return True

    fetched = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for name, slug in remaining.items():
            url = UNIVERSE_CHAMPION_URL.format(slug=slug)
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(2000)

                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                related = []
                related_container = soup.find("ul", class_=re.compile(r"shouldScroll|champions_"))
                if related_container:
                    for li in related_container.find_all("li"):
                        link = li.find("a")
                        if link:
                            name_el = li.find("h6") or li.find(class_=re.compile(r"Xin|name"))
                            if name_el:
                                related.append(name_el.get_text(strip=True))
                            else:
                                href = link.get("href", "")
                                champ_slug = href.rstrip("/").split("/")[-1]
                                related.append(champ_slug)

                region = "Runeterra"
                region_section = soup.find(string=re.compile(r"REGION"))
                if region_section:
                    parent = region_section.find_parent("div")
                    if parent:
                        region_text = parent.get_text(strip=True).replace("REGION", "").strip()
                        if region_text:
                            region = region_text

                race = ""
                race_section = soup.find(string=re.compile(r"^RACE$"))
                if race_section:
                    parent = race_section.find_parent("div")
                    if parent:
                        race = parent.get_text(strip=True).replace("RACE", "").strip()

                role = ""
                role_section = soup.find(string=re.compile(r"^ROLE$"))
                if role_section:
                    parent = role_section.find_parent("div")
                    if parent:
                        role = parent.get_text(strip=True).replace("ROLE", "").strip()

                existing[name] = {
                    "champion_name": [name],
                    "region": [region],
                    "related": related if related else [""],
                    "race": [race],
                    "role": [role],
                }
                fetched += 1
                log.info(f"  {name}: region={region}, race={race}, role={role}, related={len(related)}")

                if fetched % 10 == 0:
                    save_results(existing)
                    log.info(f"  [checkpoint] {len(existing)}/{len(slugs)} total")

            except Exception as e:
                log.warning(f"  {name}: error — {e}")

            time.sleep(0.5)

        browser.close()

    if fetched > 0:
        save_results(existing)

    return fetched > 0 or len(existing) > 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    if args.merge_only:
        if args.skip_merge:
            log.info("--merge-only and --skip-merge were both provided; nothing to do.")
            return
        run_canonical_pipeline(rebuild_graph=args.rebuild_graph)
        return

    # Step 1: Get champion list from Data Dragon
    try:
        slugs = get_champion_slugs()
    except Exception as e:
        log.error(f"Failed to fetch champion list from Data Dragon: {e}")
        log.info("Falling back to existing champions_new.json for champion names...")
        existing = Path("champions_new.json")
        if existing.exists():
            with open(existing) as f:
                data = json.load(f)
            slugs = {}
            for entry in data:
                name = entry["champion_name"][0]
                slug = SLUG_OVERRIDES.get(name, re.sub(r"[^a-zA-Z]", "", name).lower())
                slugs[name] = slug
        else:
            log.error("No fallback data available. Exiting.")
            sys.exit(1)

    # Step 2: Load existing progress
    existing = load_existing()
    if existing:
        log.info(f"Loaded {len(existing)} previously fetched champions from {OUTPUT_FILE}")

    remaining_count = len(slugs) - len(set(existing) & set(slugs))
    if remaining_count == 0:
        log.info(f"All {len(slugs)} champions already fetched! Nothing to do.")
        log.info(f"Delete {OUTPUT_FILE} to re-fetch everything.")
        if not args.skip_merge:
            run_canonical_pipeline(rebuild_graph=args.rebuild_graph)
        return

    log.info(f"{remaining_count} champions still need fetching")

    # Step 3: Try each fetch strategy in order
    success = fetch_via_meeps(slugs, existing)

    if not success:
        success = fetch_via_html_scrape(slugs, existing)

    if not success:
        success = fetch_via_playwright(slugs, existing)

    if not success and not existing:
        log.error("All strategies failed. Check your network connection and try again.")
        log.info("Tips:")
        log.info("  - The meeps API may require VPN or specific region")
        log.info("  - For Playwright: pip install playwright && playwright install chromium")
        sys.exit(1)

    # Step 4: Summary
    total = len(existing)
    still_missing = len(slugs) - len(set(existing) & set(slugs))
    if still_missing > 0:
        log.info(f"{still_missing} champions still missing — run again to retry them")
    else:
        log.info(f"All {total} champions fetched successfully!")

    if not args.skip_merge:
        run_canonical_pipeline(rebuild_graph=args.rebuild_graph)


if __name__ == "__main__":
    main()
