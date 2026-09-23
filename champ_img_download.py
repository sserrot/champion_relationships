"""Download missing champion portraits from Riot's current public assets."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from champion_normalization import normalize_name_key
from community_analysis import champion_to_image_filename
from fetch_champion_data import CHAMPION_URL, HEADERS, ROSTER_URL, VERSIONS_URL, fetch_json


ROOT = Path(__file__).resolve().parent
IMAGE_DIR = ROOT / "R_analysis" / "img"
SOURCE_FILE = ROOT / "portrait_sources.json"


def download_image(url, expected_format):
    with urlopen(Request(url, headers=HEADERS), timeout=25) as response:
        content = response.read()
    signatures = {"png": b"\x89PNG\r\n\x1a\n", "jpg": b"\xff\xd8\xff"}
    if not content.startswith(signatures[expected_format]):
        raise ValueError(f"Unexpected image format from {url}")
    return content


def main():
    champions = json.loads((ROOT / "champions_canonical.json").read_text(encoding="utf-8"))
    missing = [entry for entry in champions if not any(
        (IMAGE_DIR / champion_to_image_filename(entry["champion_name"][0])).with_suffix(extension).is_file()
        for extension in (".png", ".jpg")
    )]
    if not missing:
        print("Every champion has a local portrait.")
        return

    version = fetch_json(VERSIONS_URL)[0]
    game_roster = fetch_json(ROSTER_URL.format(version=version))["data"]
    game_by_name = {normalize_name_key(item["name"]): item for item in game_roster.values()}
    sources = json.loads(SOURCE_FILE.read_text(encoding="utf-8")) if SOURCE_FILE.exists() else {}
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    for entry in missing:
        name = entry["champion_name"][0]
        game_champion = game_by_name.get(normalize_name_key(name))
        if game_champion:
            url = f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{game_champion['image']['full']}"
            extension = ".png"
        else:
            slug = entry["_source"]["page"].rstrip("/").split("/")[-1]
            payload = fetch_json(CHAMPION_URL.format(slug=slug))
            champion = payload["champion"]
            if normalize_name_key(champion["name"]) != normalize_name_key(name):
                raise ValueError(f"Portrait identity mismatch for {name}")
            url = champion["image"]["uri"]
            extension = ".jpg"
        destination = (IMAGE_DIR / champion_to_image_filename(name)).with_suffix(extension)
        content = download_image(url, extension[1:])
        destination.write_bytes(content)
        sources[name] = {
            "file": destination.name,
            "source": url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        print(f"Added {destination.name} for {name}")

    SOURCE_FILE.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
