NAME_ALIASES = {
    "monkeyking": "Wukong",
    "wukong": "Wukong",
}


def normalize_name_key(name):
    """Normalize scraped slugs and display names to a comparable champion key."""
    if not name:
        return ""
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def normalize_champion_name(name, canonical_names=None):
    """Return the canonical display name for a champion, when known."""
    key = normalize_name_key(name)
    if not key:
        return ""
    if key in NAME_ALIASES:
        return NAME_ALIASES[key]
    if canonical_names and key in canonical_names:
        return canonical_names[key]
    return str(name).strip()
