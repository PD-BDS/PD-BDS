"""Unit tests for the pure helpers in build_cards.py (run: python -m unittest discover scripts)."""
import unittest

import build_cards as bc


class AggregateBytesTest(unittest.TestCase):
    def test_sums_across_repositories(self):
        totals = bc.aggregate_bytes([{"Python": 10, "TypeScript": 5}, {"Python": 20}])
        self.assertEqual(totals, {"Python": 30, "TypeScript": 5})

    def test_empty_input(self):
        self.assertEqual(bc.aggregate_bytes([]), {})


class VisibleOnlyTest(unittest.TestCase):
    def test_hides_notebooks_and_markup(self):
        totals = {"Jupyter Notebook": 1000, "HTML": 50, "Python": 10, "TypeScript": 2}
        self.assertEqual(bc.visible_only(totals), {"Python": 10, "TypeScript": 2})


class CommitWeightedTest(unittest.TestCase):
    def test_spreads_commits_by_visible_share(self):
        repos = [(10, {"Python": 90, "TypeScript": 10, "Jupyter Notebook": 900}),
                 (5, {"Python": 100})]
        totals = bc.commit_weighted(repos)
        self.assertAlmostEqual(totals["Python"], 9 + 5)
        self.assertAlmostEqual(totals["TypeScript"], 1)
        self.assertNotIn("Jupyter Notebook", totals)

    def test_skips_repos_without_visible_code(self):
        self.assertEqual(bc.commit_weighted([(7, {"HTML": 10})]), {})


class RankWithOtherTest(unittest.TestCase):
    def test_orders_and_folds_tail_into_other(self):
        totals = {"Python": 950, "TypeScript": 38, "PowerShell": 6, "Shell": 3, "JavaScript": 2, "Dockerfile": 1}
        rows = bc.rank_with_other(totals, top_n=4)
        self.assertEqual([n for n, _ in rows], ["Python", "TypeScript", "PowerShell", "Shell", "Other"])
        self.assertAlmostEqual(sum(p for _, p in rows), 100.0)

    def test_no_other_when_everything_fits(self):
        rows = bc.rank_with_other({"Python": 3, "TypeScript": 1}, top_n=4)
        self.assertEqual([n for n, _ in rows], ["Python", "TypeScript"])

    def test_empty(self):
        self.assertEqual(bc.rank_with_other({}), [])


class FormatPctTest(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(bc.format_pct(95.34), "95.3%")
        self.assertEqual(bc.format_pct(3.8), "3.8%")
        self.assertEqual(bc.format_pct(0.04), "<0.1%")


class RenderCardTest(unittest.TestCase):
    def test_contains_title_rows_and_no_external_refs(self):
        svg = bc.render_card("Top languages by repo", "code size across 18 public repos",
                             [("Python", 95.3), ("TypeScript", 3.8), ("Other", 0.9)])
        self.assertIn("<svg", svg)
        self.assertIn("Top languages by repo", svg)
        self.assertIn(">Python<", svg)
        self.assertIn(">TypeScript<", svg)
        self.assertIn("95.3%", svg)
        self.assertNotIn("http://", svg.replace("http://www.w3.org/2000/svg", ""))
        self.assertNotIn("<script", svg)

    def test_escapes_markup(self):
        svg = bc.render_card("A & B", "<x>", [("C++", 100.0)])
        self.assertIn("A &amp; B", svg)
        self.assertIn("&lt;x&gt;", svg)


if __name__ == "__main__":
    unittest.main()
