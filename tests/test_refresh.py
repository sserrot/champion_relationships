import unittest

from fetch_champion_data import parse_champion
from merge_champion_data import merge_entry


class LiveDataExtractionTests(unittest.TestCase):
    def test_renata_fields_and_related_names_use_verified_source(self):
        payload = {
            "champion": {
                "name": "Renata Glasc", "slug": "renataglasc",
                "associated-faction-slug": "zaun",
                "roles": [{"name": "Support"}], "races": [],
            },
            "related-champions": [
                {"slug": "camille"}, {"slug": "ekko"},
                {"slug": "viktor"}, {"slug": "zeri"},
            ],
        }
        roster = {slug: slug.title() for slug in ("camille", "ekko", "viktor", "zeri")}
        entry = parse_champion("Renata Glasc", "renataglasc", payload, roster, "2026-09-22T00:00:00+00:00")
        self.assertEqual(entry["region"], ["Zaun"])
        self.assertEqual(entry["role"], ["Support"])
        self.assertEqual(entry["related"], ["Camille", "Ekko", "Viktor", "Zeri"])

    def test_verified_empty_related_does_not_fall_back_to_old_links(self):
        payload = {
            "champion": {"name": "Amumu", "slug": "amumu", "associated-faction-slug": "shurima", "roles": [{"name": "Tank"}], "races": []},
            "related-champions": [],
        }
        updated = parse_champion("Amumu", "amumu", payload, {}, "2026-09-22T00:00:00+00:00")
        base = {"region": ["Shurima"], "related": ["Annie"], "race": [""], "role": ["Tank"]}
        merged = merge_entry("Amumu", base, updated, {"amumu": "Amumu", "annie": "Annie"})
        self.assertEqual(merged["related"], [])
        self.assertEqual(merged["_source"]["related_status"], "verified_empty")

    def test_missing_fields_and_unresolved_related_champions_fail_closed(self):
        payload = {
            "champion": {"name": "Renata Glasc", "slug": "renataglasc", "associated-faction-slug": "zaun", "roles": [], "races": []},
            "related-champions": [],
        }
        with self.assertRaisesRegex(ValueError, "missing roles"):
            parse_champion("Renata Glasc", "renataglasc", payload, {}, "now")
        payload["champion"]["roles"] = [{"name": "Support"}]
        payload["related-champions"] = [{"slug": "unknown"}]
        with self.assertRaisesRegex(ValueError, "unresolved related"):
            parse_champion("Renata Glasc", "renataglasc", payload, {}, "now")


if __name__ == "__main__":
    unittest.main()
