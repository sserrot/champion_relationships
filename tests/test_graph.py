import unittest

from community_analysis import build_graph, load_data_new, load_data_old


class RelationshipTypingTests(unittest.TestCase):
    def test_specific_label_overrides_generic_and_conflict_stays_visible(self):
        current = {
            "Alpha": {"region": "Demacia", "role": "Fighter", "race": "", "related": ["Beta", "Gamma"]},
            "Beta": {"region": "Demacia", "role": "Mage", "race": "", "related": ["Alpha"]},
            "Gamma": {"region": "Noxus", "role": "Mage", "race": "", "related": []},
        }
        older = {
            "Alpha": {"faction": "", "friends": ["Beta", "Gamma"], "rivals": ["Gamma"]},
            "Beta": {"faction": "", "friends": [], "rivals": []},
        }
        graph = build_graph(current, older)
        self.assertEqual(graph["Alpha"]["Beta"]["relation"], "friend")
        self.assertEqual(graph["Alpha"]["Gamma"]["relation"], "mixed")
        self.assertEqual(graph["Alpha"]["Gamma"]["evidence"], ["friend", "related", "rival"])
        self.assertEqual(graph.number_of_edges(), 2)

    def test_checked_in_snapshot_has_reviewable_conflicts(self):
        graph = build_graph(load_data_new(), load_data_old())
        self.assertEqual(graph.number_of_nodes(), 174)
        self.assertEqual(graph.number_of_edges(), 581)
        self.assertEqual(sum(data["relation"] == "mixed" for _, _, data in graph.edges(data=True)), 5)
        self.assertEqual(graph["Garen"]["Lux"]["relation"], "friend")
        self.assertEqual(set(graph.neighbors("Renata Glasc")), {"Camille", "Ekko", "Viktor", "Zeri"})
        self.assertTrue(graph.has_edge("Norra", "Yuumi"))


if __name__ == "__main__":
    unittest.main()
