"""
Fetch League of Legends champion lore data (related champions, region, race, role).

Strategy:
  1. Primary: Hit the undocumented universe-meeps JSON API endpoints
  2. Fallback: Scrape the Universe site using requests + BeautifulSoup
  3. Last resort: Use Playwright (headless browser) for JS-rendered content

Usage:
  pip install requests beautifulsoup4 lxml
  python fetch_champion_data.py

Optional (for fallback headless scraping):
  pip install playwright && playwright install chromium
"""

import json
import os
import re
import sys
import time
import logging
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

DDRAGON_VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
DDRAGON_CHAMPIONS_URL = "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
MEEPS_CHAMPION_URL = "https://universe-meeps.leagueoflegends.com/v1/en_us/champion/{slug}/index.json"
MEEPS_BROWSE_URL = "https://universe-meeps.leagueoflegends.com/v1/en_us/champion-browse/index.json"
UNIVERSE_CHAMPION_URL = "https://universe.leagueoflegends.com/en_us/champion/{slug}/"

OUTPUT_FILE = "champions_updated.json"

# Mapping of special champion name -> universe slug
SLUG_OVERRIDES = {
    "Wukong": "monkeyking",
    "Renata Glasc": "renata",
    "Nunu & Willump": "nunu",
}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://universe.leagueoflegends.com/",
    "Origin": "https://universe.leagueoflegends.com",
})


def get_champion_slugs() -> dict[str, str]:
    """Get champion name -> slug mapping from Data Dragon."""
    log.info("Fetching champion list from Data Dragon...")
    resp = SESSION.get(DDRAGON_VERSIONS_URL, timeout=10)
    resp.raise_for_status()
    version = resp.json()[0]
    log.info(f"Latest game version: {version}")

    resp = SESSION.get(DDRAGON_CHAMPIONS_URL.format(version=version), timeout=10)
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

def fetch_via_meeps(slugs: dict[str, str]) -> Optional[list[dict]]:
    """Try the undocumented universe-meeps API."""
    log.info("Attempting universe-meeps API...")

    # Quick test with a single champion
    test_url = MEEPS_CHAMPION_URL.format(slug="aatrox")
    try:
        resp = SESSION.get(test_url, timeout=10)
        if resp.status_code != 200:
            log.warning(f"Meeps API returned {resp.status_code} — skipping this strategy")
            return None
    except requests.RequestException as e:
        log.warning(f"Meeps API unreachable: {e}")
        return None

    log.info("Meeps API accessible! Fetching all champions...")
    results = []
    for name, slug in slugs.items():
        url = MEEPS_CHAMPION_URL.format(slug=slug)
        try:
            resp = SESSION.get(url, timeout=10)
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

            results.append({
                "champion_name": [name],
                "region": [region if region else "Runeterra"],
                "related": related if related else [""],
                "race": [race],
                "role": [role],
            })
            log.info(f"  {name}: {len(related)} related champions")

        except Exception as e:
            log.warning(f"  {name}: error — {e}")

        time.sleep(0.2)  # Rate limit

    return results if results else None


# ---------------------------------------------------------------------------
# Strategy 2: Scrape Universe HTML (works if server-side rendered)
# ---------------------------------------------------------------------------

def fetch_via_html_scrape(slugs: dict[str, str]) -> Optional[list[dict]]:
    """Scrape the Universe champion pages directly."""
    log.info("Attempting HTML scrape of Universe site...")

    test_url = UNIVERSE_CHAMPION_URL.format(slug="aatrox")
    try:
        resp = SESSION.get(test_url, timeout=15)
        if resp.status_code != 200:
            log.warning(f"Universe site returned {resp.status_code}")
            return None
        # Check if content is server-rendered or just a JS shell
        if "related" not in resp.text.lower() and "relatedChampions" not in resp.text:
            log.warning("Universe page appears to be JS-rendered only — HTML scrape won't work")
            return None
    except requests.RequestException as e:
        log.warning(f"Universe site unreachable: {e}")
        return None

    log.info("Universe site accessible with content! Scraping all champions...")
    results = []
    for name, slug in slugs.items():
        url = UNIVERSE_CHAMPION_URL.format(slug=slug)
        try:
            resp = SESSION.get(url, timeout=15)
            if resp.status_code != 200:
                log.warning(f"  {name}: HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Try to find embedded JSON data (some React sites embed state)
            scripts = soup.find_all("script")
            champion_json = None
            for script in scripts:
                if script.string and ("related-champions" in script.string or "relatedChampions" in script.string):
                    # Try to extract JSON from script tag
                    match = re.search(r'(\{.*"champion".*\})', script.string, re.DOTALL)
                    if match:
                        try:
                            champion_json = json.loads(match.group(1))
                        except json.JSONDecodeError:
                            pass

            if champion_json:
                # Parse embedded JSON same as meeps approach
                cdata = champion_json.get("champion", champion_json)
                related = [r.get("name", "") for r in cdata.get("related-champions", [])]
                region = cdata.get("associated-faction-slug", "").replace("-", " ").title() or "Runeterra"
                race = ""
                role = ""
            else:
                # Fall back to HTML parsing (similar to existing spider)
                related = []
                related_section = soup.find("ul", class_=re.compile(r"relatedChampions|champion.*grid|shouldScroll"))
                if related_section:
                    for li in related_section.find_all("li"):
                        link = li.find("a")
                        if link and link.get("href", "").startswith("/en_us/champion/"):
                            # Extract name from text or href
                            champ_name_el = li.find("h6") or li.find("div", class_=re.compile(r"champ"))
                            if champ_name_el:
                                related.append(champ_name_el.get_text(strip=True))
                            else:
                                # Derive from href
                                href_slug = link["href"].rstrip("/").split("/")[-1]
                                related.append(href_slug.title())

                # Region
                region_el = soup.find("div", class_=re.compile(r"race_|region"))
                region = region_el.get_text(strip=True) if region_el else "Runeterra"

                # Race - look for the race section from the screenshot DOM
                race = ""
                race_el = soup.find("div", class_=re.compile(r"race_"))
                if race_el:
                    race = race_el.get_text(strip=True)

                # Role
                role = ""
                role_el = soup.find(string=re.compile(r"^(Fighter|Mage|Assassin|Marksman|Tank|Support)$"))
                if role_el:
                    role = role_el.strip()

            results.append({
                "champion_name": [name],
                "region": [region],
                "related": related if related else [""],
                "race": [race],
                "role": [role],
            })
            log.info(f"  {name}: {len(related)} related")

        except Exception as e:
            log.warning(f"  {name}: error — {e}")

        time.sleep(0.3)

    return results if results else None


# ---------------------------------------------------------------------------
# Strategy 3: Playwright headless browser
# ---------------------------------------------------------------------------

def fetch_via_playwright(slugs: dict[str, str]) -> Optional[list[dict]]:
    """Use Playwright to render JS and scrape the fully loaded page."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.warning("Playwright not installed. Install with: pip install playwright && playwright install chromium")
        return None

    log.info("Using Playwright headless browser...")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for name, slug in slugs.items():
            url = UNIVERSE_CHAMPION_URL.format(slug=slug)
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                # Wait for the related champions section to load
                page.wait_for_timeout(2000)

                # Try to intercept the meeps API response from network
                # Or parse the rendered DOM
                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                # Related champions - from the screenshot we can see the DOM structure
                related = []
                # Look for champion links in the related section
                related_links = soup.select('a[href*="/en_us/champion/"]')
                # Filter to only those in the related champions container
                related_container = soup.find("ul", class_=re.compile(r"shouldScroll|champions_"))
                if related_container:
                    for li in related_container.find_all("li"):
                        link = li.find("a")
                        if link:
                            # Get champion name from h6 or similar element
                            name_el = li.find("h6") or li.find(class_=re.compile(r"Xin|name"))
                            if name_el:
                                related.append(name_el.get_text(strip=True))
                            else:
                                href = link.get("href", "")
                                champ_slug = href.rstrip("/").split("/")[-1]
                                related.append(champ_slug)

                # Region
                region = "Runeterra"
                region_section = soup.find(string=re.compile(r"REGION"))
                if region_section:
                    parent = region_section.find_parent("div")
                    if parent:
                        region_text = parent.get_text(strip=True).replace("REGION", "").strip()
                        if region_text:
                            region = region_text

                # Race
                race = ""
                race_section = soup.find(string=re.compile(r"^RACE$"))
                if race_section:
                    parent = race_section.find_parent("div")
                    if parent:
                        race = parent.get_text(strip=True).replace("RACE", "").strip()

                # Role
                role = ""
                role_section = soup.find(string=re.compile(r"^ROLE$"))
                if role_section:
                    parent = role_section.find_parent("div")
                    if parent:
                        role = parent.get_text(strip=True).replace("ROLE", "").strip()

                results.append({
                    "champion_name": [name],
                    "region": [region],
                    "related": related if related else [""],
                    "race": [race],
                    "role": [role],
                })
                log.info(f"  {name}: region={region}, race={race}, role={role}, related={len(related)}")

            except Exception as e:
                log.warning(f"  {name}: error — {e}")

            time.sleep(0.5)

        browser.close()

    return results if results else None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
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

    # Step 2: Try each fetch strategy in order
    results = None

    # Strategy 1: Meeps API
    results = fetch_via_meeps(slugs)

    # Strategy 2: HTML scrape
    if not results:
        results = fetch_via_html_scrape(slugs)

    # Strategy 3: Playwright
    if not results:
        results = fetch_via_playwright(slugs)

    if not results:
        log.error("All strategies failed. Check your network connection and try again.")
        log.info("Tips:")
        log.info("  - The meeps API may require VPN or specific region")
        log.info("  - For Playwright: pip install playwright && playwright install chromium")
        sys.exit(1)

    # Step 3: Sort and save
    results.sort(key=lambda x: x["champion_name"][0])

    output_path = Path(OUTPUT_FILE)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    log.info(f"Saved {len(results)} champions to {output_path}")
    log.info(f"Champions with relationships: {sum(1 for r in results if r['related'] != [''])}")


if __name__ == "__main__":
    main()
