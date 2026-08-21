"""Unit tests for build_cards.py (run: python -m unittest discover -s scripts -q)."""
import os
import unittest
import xml.dom.minidom
from unittest import mock

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
        totals = {"Python": 950, "TypeScript": 38, "PowerShell": 6, "Shell": 3,
                  "JavaScript": 2, "Dockerfile": 1}
        rows = bc.rank_with_other(totals, top_n=4)
        self.assertEqual([n for n, _ in rows], ["Python", "TypeScript", "PowerShell", "Shell", "Other"])
        self.assertAlmostEqual(sum(p for _, p in rows), 100.0)

    def test_no_other_when_everything_fits(self):
        rows = bc.rank_with_other({"Python": 3, "TypeScript": 1}, top_n=4)
        self.assertEqual([n for n, _ in rows], ["Python", "TypeScript"])

    def test_empty(self):
        self.assertEqual(bc.rank_with_other({}), [])


class FormatPctTest(unittest.TestCase):
    def test_formats_and_boundaries(self):
        self.assertEqual(bc.format_pct(95.34), "95.3%")
        self.assertEqual(bc.format_pct(10.0), "10.0%")
        self.assertEqual(bc.format_pct(3.8), "3.8%")
        self.assertEqual(bc.format_pct(0.1), "0.1%")
        self.assertEqual(bc.format_pct(0.04), "<0.1%")
        self.assertEqual(bc.format_pct(100.0), "100.0%")


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
        xml.dom.minidom.parseString(svg)

    def test_escapes_markup_in_every_text_slot(self):
        svg = bc.render_card("A & B", "<x>", [("C<&>D", 99.95), ("Other", 0.05)])
        self.assertIn("A &amp; B", svg)
        self.assertIn("&lt;x&gt;", svg)
        self.assertIn("C&lt;&amp;&gt;D", svg)
        self.assertIn("&lt;0.1%", svg)
        xml.dom.minidom.parseString(svg)

    def test_empty_rows_still_well_formed(self):
        xml.dom.minidom.parseString(bc.render_card("Empty", "nothing", []))


class PagedTest(unittest.TestCase):
    def test_follows_pages_until_short_batch(self):
        pages = [[{"i": n} for n in range(100)], [{"i": 100}, {"i": 101}]]
        with mock.patch.object(bc, "_request", side_effect=pages) as req:
            items = bc._paged(f"{bc.API}/users/x/repos?type=owner", "tok")
        self.assertEqual(len(items), 102)
        self.assertEqual(req.call_count, 2)
        self.assertIn("&per_page=100&page=2", req.call_args_list[1].args[0])

    def test_raises_on_non_list_payload(self):
        with mock.patch.object(bc, "_request", return_value={"message": "Bad credentials"}):
            with self.assertRaises(RuntimeError):
                bc._paged(f"{bc.API}/users/x/repos", "tok")


class ListReposTest(unittest.TestCase):
    def test_filters_forks_archived_and_other_owners(self):
        payload = [
            {"full_name": "pd/a", "fork": False, "archived": False, "owner": {"login": "PD"}},
            {"full_name": "pd/b", "fork": True, "archived": False, "owner": {"login": "PD"}},
            {"full_name": "pd/c", "fork": False, "archived": True, "owner": {"login": "PD"}},
            {"full_name": "other/d", "fork": False, "archived": False, "owner": {"login": "other"}},
        ]
        with mock.patch.object(bc, "_paged", return_value=payload):
            repos = bc.list_repos("pd", "tok", include_private=False)
        self.assertEqual([r["full_name"] for r in repos], ["pd/a"])

    def test_rejects_invalid_username(self):
        with self.assertRaises(ValueError):
            bc.list_repos("bad/name?x", "tok", include_private=False)


class CommitContributionsTest(unittest.TestCase):
    @staticmethod
    def _bucket(count, is_fork=False, languages=None):
        return {"contributions": {"totalCount": count},
                "repository": {"nameWithOwner": "pd/x", "isFork": is_fork, "languages": languages}}

    def test_parses_buckets_and_skips_forks_and_null_languages(self):
        data = {"data": {"user": {"contributionsCollection": {"commitContributionsByRepository": [
            self._bucket(7, languages={"edges": [{"size": 90, "node": {"name": "Python"}},
                                                 {"size": 10, "node": {"name": "TypeScript"}}]}),
            self._bucket(3, is_fork=True, languages={"edges": []}),
            self._bucket(2, languages=None),
        ]}}}}
        with mock.patch.object(bc, "_request", return_value=data):
            result = bc.commit_contributions("pd", "tok")
        self.assertEqual(result, [(7, {"Python": 90, "TypeScript": 10}), (2, {})])

    def test_raises_on_graphql_errors(self):
        with mock.patch.object(bc, "_request", return_value={"errors": [{"message": "nope"}]}):
            with self.assertRaises(RuntimeError):
                bc.commit_contributions("pd", "tok")


class MainGuardTest(unittest.TestCase):
    def test_refuses_to_write_cards_when_no_data(self):
        env = {"USERNAME": "pd", "GITHUB_TOKEN": "tok"}
        with mock.patch.dict(os.environ, env, clear=False), \
                mock.patch.object(bc, "list_repos", return_value=[]), \
                mock.patch.object(bc, "commit_contributions", return_value=[]), \
                mock.patch.object(bc.Path, "write_text") as write:
            self.assertEqual(bc.main(), 1)
        write.assert_not_called()

    def test_requires_username_and_token(self):
        with mock.patch.dict(os.environ, {"USERNAME": "", "GITHUB_TOKEN": "", "PROFILE_TOKEN": ""}):
            self.assertEqual(bc.main(), 2)


if __name__ == "__main__":
    unittest.main()
