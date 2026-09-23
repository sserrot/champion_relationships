import json
import re
import unittest
from pathlib import Path

from server import app


ROOT = Path(__file__).resolve().parents[1]


class PortfolioOutputTests(unittest.TestCase):
    def test_static_demo_contains_every_referenced_portrait_and_local_assets(self):
        page = (ROOT / "demo" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "portfolio.js").read_text(encoding="utf-8")
        for element_id in set(re.findall(r"\$\('([^']+)'\)", script)):
            self.assertIn(f'id="{element_id}"', page, element_id)
        match = re.search(r'<script id="graph-data" type="application/json">(.*?)</script>', page, re.S)
        self.assertIsNotNone(match)
        graph = json.loads(match.group(1))
        self.assertEqual((len(graph["nodes"]), len(graph["edges"])), (174, 581))
        self.assertFalse([node["id"] for node in graph["nodes"] if not node["image"]])
        self.assertEqual(sum(edge["relation"] == "mixed" for edge in graph["edges"]), 5)
        self.assertTrue(all(node["url"].startswith("https://universe.leagueoflegends.com/en_US/champion/") for node in graph["nodes"]))
        self.assertIn('id="detail-source"', page)
        self.assertIn('href="previous.html">Compare with previous graph', page)
        for node in graph["nodes"]:
            if node["image"]:
                self.assertTrue((ROOT / "demo" / graph["imagePrefix"] / node["image"]).is_file(), node["id"])
        for asset in ("portfolio.css", "portfolio.js", "vis-network.min.js"):
            self.assertTrue((ROOT / "demo" / "assets" / asset).is_file())
        self.assertNotIn("https://unpkg.com", page)

        previous = (ROOT / "demo" / "previous.html").read_text(encoding="utf-8")
        self.assertIn('href="index.html">Current graph', previous)
        self.assertIn('src="assets/vis-network.min.js"', previous)
        self.assertNotIn("{{ url_for", previous)
        for filename in set(re.findall(r'assets/img/([^"/]+)', previous)):
            self.assertTrue((ROOT / "demo" / "assets" / "img" / filename).is_file(), filename)

    def test_home_is_explorer_and_report_remains_available(self):
        client = app.test_client()
        home = client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b"Find a champion", home.data)
        self.assertEqual(client.get("/network").status_code, 200)
        previous = client.get("/previous")
        self.assertEqual(previous.status_code, 200)
        self.assertIn(b"Hide champion:", previous.data)
        self.assertEqual(client.get("/report").status_code, 200)
        image_response = client.get("/img/garen.png")
        self.assertEqual(image_response.status_code, 200)
        image_response.close()


if __name__ == "__main__":
    unittest.main()
