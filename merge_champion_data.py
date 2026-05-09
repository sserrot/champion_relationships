"""Merge champion relationship datasets into one canonical JSON file."""

import json

from champion_normalization import normalize_champion_name, normalize_name_key


BASE_PATH = "champions_new.json"
UPDATED_PATH = "champions_updated.json"
OUTPUT_PATH = "champions_canonical.json"


def first_value(entry, field):
    values = entry.get(field, [""])
    if not values:
        return ""
    return values[0]


def load_entries(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_canonical_name_map(*datasets):
    canonical = {}
    for data in datasets:
        for entry in data:
            name = normalize_champion_name(first_value(entry, "champion_name"))
            if name:
                canonical[normalize_name_key(name)] = name
    return canonical


def normalize_related(values, canonical_names):
    related = []
    seen = set()
    for value in values:
        name = normalize_champion_name(value, canonical_names)
        key = normalize_name_key(name)
        if not key or key in seen:
            continue
        seen.add(key)
        related.append(name)
    return related


def entry_by_key(data, canonical_names):
    entries = {}
    for entry in data:
        name = normalize_champion_name(first_value(entry, "champion_name"), canonical_names)
        key = normalize_name_key(name)
        if key:
            entries[key] = entry
    return entries


def merge_entry(name, base_entry, updated_entry, canonical_names):
    source = updated_entry or base_entry
    fallback = base_entry or {}

    region = first_value(source, "region")
    fallback_region = first_value(fallback, "region")
    if not region or (region == "Runeterra" and fallback_region and fallback_region != "Runeterra"):
        region = fallback_region

    race = first_value(source, "race") or first_value(fallback, "race")
    role = first_value(source, "role") or first_value(fallback, "role")

    related_source = source.get("related", [])
    if not related_source:
        related_source = fallback.get("related", [])

    return {
        "champion_name": [name],
        "region": [region],
        "related": normalize_related(related_source, canonical_names),
        "race": [race],
        "role": [role],
    }


def main():
    base_data = load_entries(BASE_PATH)
    updated_data = load_entries(UPDATED_PATH)
    canonical_names = build_canonical_name_map(base_data, updated_data)
    base_by_key = entry_by_key(base_data, canonical_names)
    updated_by_key = entry_by_key(updated_data, canonical_names)

    merged = []
    for key in sorted(set(base_by_key) | set(updated_by_key), key=lambda k: canonical_names[k]):
        merged.append(
            merge_entry(
                canonical_names[key],
                base_by_key.get(key),
                updated_by_key.get(key),
                canonical_names,
            )
        )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(merged)} champions to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
