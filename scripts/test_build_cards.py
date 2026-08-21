"""Unit tests for build_cards.py (run: python -m unittest discover -s scripts -q)."""
import os
import unittest
import urllib.request
import xml.dom.minidom
from unittest import mock

import build_cards as bc

DARK, LIGHT = bc.THEMES["dark"], bc.THEMES["light"]


def _contrib_payload(buckets=None, weeks=None, total=0):
    return {"data": {"user": {"contributionsCollection": {
        "contributionCalendar": {"totalContributions": total, "weeks": weeks or []},
        "commitContributionsByRepository": buckets or [],
    }}}}


def _bucket(count, is_fork=False, languages=None):
    return {"contributions": {"totalCount": count},
            "repository": {"nameWithOwner": "pd/x", "isFork": is_fork, "languages": languages}}


def _week(start, *counts):
    year, month, day = (int(x) for x in start.split("-"))
    return {"contributionDays": [
        {"date": f"{year:04d}-{month:02d}-{day + i:02d}", "contributionCount": c}
        for i, c in enumerate(counts)]}


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


class MergeAliasesTest(unittest.TestCase):
    def test_groups_js_and_ts_under_one_label(self):
        merged = bc.merge_aliases({"Python": 80, "JavaScript": 15, "TypeScript": 2, "Shell": 1})
        self.assertEqual(merged, {"Python": 80, "TypeScript / JavaScript": 17, "Shell": 1})

    def test_identity_without_aliases(self):
        self.assertEqual(bc.merge_aliases({"Python": 1}, aliases={}), {"Python": 1})


class FormatPctTest(unittest.TestCase):
    def test_formats_and_boundaries(self):
        self.assertEqual(bc.format_pct(95.34), "95.3%")
        self.assertEqual(bc.format_pct(10.0), "10.0%")
        self.assertEqual(bc.format_pct(0.1), "0.1%")
        self.assertEqual(bc.format_pct(0.04), "<0.1%")
        self.assertEqual(bc.format_pct(100.0), "100.0%")


class ParseContributionsTest(unittest.TestCase):
    def test_commit_buckets_skip_forks_and_null_languages(self):
        data = _contrib_payload(buckets=[
            _bucket(7, languages={"edges": [{"size": 90, "node": {"name": "Python"}},
                                            {"size": 10, "node": {"name": "TypeScript"}}]}),
            _bucket(3, is_fork=True, languages={"edges": []}),
            _bucket(2, languages=None),
        ])
        self.assertEqual(bc.parse_commit_buckets(data),
                         [(7, {"Python": 90, "TypeScript": 10}), (2, {})])

    def test_calendar_weekly_sums_and_starts(self):
        data = _contrib_payload(weeks=[_week("2026-01-04", 1, 2, 0), _week("2026-01-11", 0, 5)],
                                total=8)
        cal = bc.parse_calendar(data)
        self.assertEqual(cal.total, 8)
        self.assertEqual(cal.weeks, (3, 5))
        self.assertEqual(cal.week_starts, ("2026-01-04", "2026-01-11"))

    def test_month_ticks_first_week_only(self):
        starts = ("2025-12-28", "2026-01-04", "2026-01-11", "2026-02-01", "2026-02-08")
        self.assertEqual(bc.month_ticks(starts), [(1, "Jan"), (3, "Feb")])


class RenderCardTest(unittest.TestCase):
    def test_contains_title_rows_and_no_external_refs(self):
        svg = bc.render_card("Top languages by repo", "code size across 18 public repos",
                             [("Python", 95.3), ("TypeScript", 3.8), ("Other", 0.9)], DARK)
        self.assertIn("Top languages by repo", svg)
        self.assertIn(">Python<", svg)
        self.assertIn(">TypeScript<", svg)
        self.assertIn("95.3%", svg)
        self.assertNotIn("http://", svg.replace("http://www.w3.org/2000/svg", ""))
        self.assertNotIn("<script", svg)
        xml.dom.minidom.parseString(svg)

    def test_escapes_markup_in_every_text_slot(self):
        svg = bc.render_card("A & B", "<x>", [("C<&>D", 99.95), ("Other", 0.05)], LIGHT)
        self.assertIn("A &amp; B", svg)
        self.assertIn("&lt;x&gt;", svg)
        self.assertIn("C&lt;&amp;&gt;D", svg)
        self.assertIn("&lt;0.1%", svg)
        xml.dom.minidom.parseString(svg)

    def test_themes_differ_and_empty_rows_parse(self):
        dark = bc.render_card("Empty", "nothing", [], DARK)
        light = bc.render_card("Empty", "nothing", [], LIGHT)
        xml.dom.minidom.parseString(dark)
        xml.dom.minidom.parseString(light)
        self.assertIn(DARK.bg, dark)
        self.assertIn(LIGHT.bg, light)
        self.assertNotEqual(dark, light)


class RenderActivityTest(unittest.TestCase):
    def test_renders_chart_total_and_stats(self):
        cal = bc.Calendar(278, (0, 4, 9, 2, 0, 7), ("2026-01-04", "2026-01-11", "2026-01-18",
                                                    "2026-01-25", "2026-02-01", "2026-02-08"))
        svg = bc.render_activity(cal, 19, 11, DARK)
        xml.dom.minidom.parseString(svg)
        self.assertIn(">278<", svg)
        self.assertIn("19 repositories", svg)
        self.assertIn("11 stars received", svg)
        self.assertIn(">Jan<", svg)
        self.assertIn(">Feb<", svg)
        self.assertIn("<path", svg)

    def test_handles_too_few_weeks_and_light_theme(self):
        svg = bc.render_activity(bc.Calendar(0, (), ()), 0, 0, LIGHT)
        xml.dom.minidom.parseString(svg)
        self.assertIn("no calendar data", svg)
        self.assertIn(LIGHT.bg, svg)


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


class FetchContributionsTest(unittest.TestCase):
    def test_raises_on_graphql_errors(self):
        with mock.patch.object(bc, "_request", return_value={"errors": [{"message": "nope"}]}):
            with self.assertRaises(RuntimeError):
                bc.fetch_contributions("pd", "tok")

    def test_raises_on_null_user(self):
        with mock.patch.object(bc, "_request", return_value={"data": {"user": None}}):
            with self.assertRaises(RuntimeError):
                bc.fetch_contributions("pd", "tok")


class RedirectTest(unittest.TestCase):
    def test_strips_token_only_on_cross_host_redirect(self):
        handler = bc._SameHostRedirect()
        req = urllib.request.Request(f"{bc.API}/x", headers={"Authorization": "Bearer t"})
        off_host = handler.redirect_request(req, None, 302, "Found", {}, "https://objects.example/y")
        same_host = handler.redirect_request(req, None, 302, "Found", {}, f"{bc.API}/z")
        self.assertFalse(off_host.has_header("Authorization"))
        self.assertTrue(same_host.has_header("Authorization"))


class MonthTicksEdgeTest(unittest.TestCase):
    def test_malformed_date_raises_value_error(self):
        with self.assertRaises(ValueError):
            bc.month_ticks(("2026-13-03",))

    def test_all_zero_weeks_show_peak_zero(self):
        cal = bc.Calendar(0, (0, 0, 0), ("2026-01-04", "2026-01-11", "2026-01-18"))
        svg = bc.render_activity(cal, 1, 0, DARK)
        xml.dom.minidom.parseString(svg)
        self.assertIn("peak 0 / week", svg)


class BuildTest(unittest.TestCase):
    def test_produces_six_themed_cards(self):
        repos = [{"full_name": "pd/a", "stargazers_count": 3}, {"full_name": "pd/b", "stargazers_count": 0}]
        data = _contrib_payload(
            buckets=[_bucket(5, languages={"edges": [{"size": 80, "node": {"name": "Python"}},
                                                     {"size": 20, "node": {"name": "TypeScript"}}]})],
            weeks=[_week("2026-01-04", 1, 1), _week("2026-01-11", 2)], total=4)
        with mock.patch.object(bc, "list_repos", return_value=repos), \
                mock.patch.object(bc, "repo_languages", side_effect=[{"Python": 100}, {"TypeScript": 50}]), \
                mock.patch.object(bc, "fetch_contributions", return_value=data):
            cards = bc._build("pd", "tok", include_private=False)
        self.assertEqual(sorted(cards), sorted(
            f"{n}-{t}.svg" for n in ("activity", "languages-by-repo", "languages-by-commit")
            for t in ("dark", "light")))
        for svg in cards.values():
            xml.dom.minidom.parseString(svg)
        self.assertIn(">4<", cards["activity-dark.svg"])
        self.assertIn(">TypeScript / JavaScript<", cards["languages-by-repo-dark.svg"])
        self.assertIn("3 stars received", cards["activity-light.svg"])

    def test_refuses_when_no_data(self):
        with mock.patch.object(bc, "list_repos", return_value=[]), \
                mock.patch.object(bc, "fetch_contributions", return_value=_contrib_payload()):
            with self.assertRaises(RuntimeError):
                bc._build("pd", "tok", include_private=False)


class FallbackTest(unittest.TestCase):
    @staticmethod
    def _http_error(code):
        import io
        import urllib.error
        return urllib.error.HTTPError("https://api.github.com/user/repos", code, "x", {}, io.BytesIO(b""))

    def test_401_on_profile_token_falls_back_to_public(self):
        calls = []

        def fake_build(user, token, include_private):
            calls.append((token, include_private))
            if include_private:
                raise self._http_error(401)
            return {"ok.svg": "<svg/>"}

        with mock.patch.object(bc, "_build", side_effect=fake_build):
            cards = bc._build_with_fallback("pd", "pat", "pat", "ghtok")
        self.assertEqual(cards, {"ok.svg": "<svg/>"})
        self.assertEqual(calls, [("pat", True), ("ghtok", False)])

    def test_other_errors_and_public_scope_are_not_swallowed(self):
        with mock.patch.object(bc, "_build", side_effect=self._http_error(403)):
            with self.assertRaises(bc.urllib.error.HTTPError):
                bc._build_with_fallback("pd", "pat", "pat", "ghtok")
        with mock.patch.object(bc, "_build", side_effect=self._http_error(401)):
            with self.assertRaises(bc.urllib.error.HTTPError):
                bc._build_with_fallback("pd", "ghtok", "", "ghtok")


class MainGuardTest(unittest.TestCase):
    def test_returns_1_and_writes_nothing_when_build_fails(self):
        env = {"PROFILE_USER": "pd", "GITHUB_TOKEN": "tok"}
        with mock.patch.dict(os.environ, env, clear=False), \
                mock.patch.object(bc, "_build", side_effect=RuntimeError("no data")), \
                mock.patch.object(bc.Path, "write_text") as write:
            self.assertEqual(bc.main(), 1)
        write.assert_not_called()

    def test_requires_username_and_token(self):
        env = {"PROFILE_USER": "", "USERNAME": "", "GITHUB_TOKEN": "", "PROFILE_TOKEN": ""}
        with mock.patch.dict(os.environ, env):
            self.assertEqual(bc.main(), 2)


if __name__ == "__main__":
    unittest.main()
