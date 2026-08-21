#!/usr/bin/env python3
"""Build the activity and language cards shown on the profile README.

Pulls data from the GitHub REST and GraphQL APIs, then renders light and dark
variants of three self-contained SVG cards into assets/readme/:

    activity-{theme}.svg             contributions over the last 12 months
    languages-by-repo-{theme}.svg    language bytes across owned repositories
    languages-by-commit-{theme}.svg  commit-weighted language shares, last year

Notebook and generated-markup languages listed in HIDDEN are left out so the
language cards reflect hand-written code.

Environment:
    PROFILE_USER   GitHub login to build cards for (required; USERNAME is accepted
                   as a fallback but Windows sets it to the OS login)
    GITHUB_TOKEN   Token for API calls; the Actions default token is enough
                   for public repositories
    PROFILE_TOKEN  Optional personal token with `repo` scope; when set, private
                   repositories and contributions are included too
"""
from __future__ import annotations

import datetime as dt
import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as _esc

API = "https://api.github.com"
API_HOST = urllib.parse.urlsplit(API).hostname
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "readme"
USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
MAX_PAGES = 50

HIDDEN = frozenset({"Jupyter Notebook", "HTML", "CSS", "Mako", "SCSS"})
TOP_N = 4  # ranked rows before everything else is folded into "Other"
# Languages shown under one label (same ecosystem); applied before ranking.
ALIASES = {"TypeScript": "TypeScript / JavaScript", "JavaScript": "TypeScript / JavaScript"}

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
CARD_W, CARD_H = 480, 290
ACT_W, ACT_H = 1200, 260
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

CONTRIB_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
      commitContributionsByRepository(maxRepositories: 100) {
        contributions { totalCount }
        repository {
          nameWithOwner
          isFork
          languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
            edges { size node { name } }
          }
        }
      }
    }
  }
}
"""

Rows = list[tuple[str, float]]


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    border: str
    fg: str
    muted: str
    track: str
    accent: str
    palette: tuple[str, ...]
    other: str


THEMES: dict[str, Theme] = {
    "dark": Theme("dark", "#0D1117", "#30363D", "#E6EDF3", "#8B949E", "#21262D", "#58A6FF",
                  ("#58A6FF", "#3FB950", "#D29922", "#A371F7", "#F778BA"), "#6E7681"),
    "light": Theme("light", "#FFFFFF", "#D0D7DE", "#1F2328", "#57606A", "#EAEEF2", "#0969DA",
                   ("#0969DA", "#1A7F37", "#9A6700", "#8250DF", "#BF3989"), "#8C959F"),
}


@dataclass(frozen=True)
class Calendar:
    total: int
    weeks: tuple[int, ...]        # contributions per week, oldest first
    week_starts: tuple[str, ...]  # ISO date of each week's first day


# --------------------------------------------------------------------------- #
# Pure data helpers (unit-tested)
# --------------------------------------------------------------------------- #
def aggregate_bytes(language_maps: Sequence[Mapping[str, int]]) -> dict[str, int]:
    """Sum language bytes across repositories."""
    totals: dict[str, int] = {}
    for langs in language_maps:
        for name, size in langs.items():
            totals[name] = totals.get(name, 0) + int(size)
    return totals


def commit_weighted(repos: Sequence[tuple[int, Mapping[str, int]]],
                    hidden: frozenset[str] = HIDDEN) -> dict[str, float]:
    """Spread each repository's commit count across its visible languages."""
    totals: dict[str, float] = {}
    for commits, langs in repos:
        visible = {k: v for k, v in langs.items() if k not in hidden and v > 0}
        size = sum(visible.values())
        if commits <= 0 or size == 0:
            continue
        for name, bytes_ in visible.items():
            totals[name] = totals.get(name, 0.0) + commits * (bytes_ / size)
    return totals


def visible_only(totals: Mapping[str, float],
                 hidden: frozenset[str] = HIDDEN) -> dict[str, float]:
    """Drop hidden languages and zero-size entries."""
    return {k: v for k, v in totals.items() if k not in hidden and v > 0}


def merge_aliases(totals: Mapping[str, float],
                  aliases: Mapping[str, str] = ALIASES) -> dict[str, float]:
    """Fold aliased languages into their shared label, summing their sizes."""
    merged: dict[str, float] = {}
    for name, val in totals.items():
        label = aliases.get(name, name)
        merged[label] = merged.get(label, 0.0) + val
    return merged


def rank_with_other(totals: Mapping[str, float], top_n: int = TOP_N) -> Rows:
    """Top-n (name, percent) rows plus an 'Other' row; percentages sum to 100."""
    grand = float(sum(totals.values()))
    if grand <= 0:
        return []
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    head = [(name, 100.0 * val / grand) for name, val in ranked[:top_n]]
    rest = sum(val for _, val in ranked[top_n:])
    if rest > 0:
        head.append(("Other", 100.0 * rest / grand))
    return head


def format_pct(pct: float) -> str:
    """Format a percentage for display; values under 0.1 become '<0.1%'."""
    return f"{pct:.1f}%" if pct >= 0.1 else "<0.1%"


def parse_commit_buckets(data: Mapping[str, Any]) -> list[tuple[int, dict[str, int]]]:
    """(commit count, language bytes) per non-fork repository from CONTRIB_QUERY."""
    buckets = data["data"]["user"]["contributionsCollection"]["commitContributionsByRepository"]
    result: list[tuple[int, dict[str, int]]] = []
    for bucket in buckets:
        repo = bucket["repository"]
        if repo.get("isFork"):
            continue
        edges = (repo.get("languages") or {}).get("edges") or []
        langs = {str(e["node"]["name"]): int(e["size"]) for e in edges}
        result.append((int(bucket["contributions"]["totalCount"]), langs))
    return result


def parse_calendar(data: Mapping[str, Any]) -> Calendar:
    """Weekly contribution totals from CONTRIB_QUERY."""
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks: list[int] = []
    starts: list[str] = []
    for week in cal.get("weeks") or []:
        days = week.get("contributionDays") or []
        if not days:
            continue
        weeks.append(sum(int(d["contributionCount"]) for d in days))
        starts.append(str(days[0]["date"]))
    return Calendar(int(cal.get("totalContributions", 0)), tuple(weeks), tuple(starts))


def month_ticks(week_starts: tuple[str, ...]) -> list[tuple[int, str]]:
    """(week index, month label) for the first week of each month."""
    ticks: list[tuple[int, str]] = []
    seen: set[tuple[int, int]] = set()
    for i, iso in enumerate(week_starts):
        day = dt.date.fromisoformat(iso)  # ValueError on malformed input
        if day.day <= 7 and (day.year, day.month) not in seen:
            seen.add((day.year, day.month))
            ticks.append((i, MONTHS[day.month - 1]))
    return ticks


# --------------------------------------------------------------------------- #
# SVG rendering
# --------------------------------------------------------------------------- #
def _frame(width: int, height: int, title: str, desc: str, t: Theme) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="t d">',
        f'  <title id="t">{_esc(title)}</title>',
        f'  <desc id="d">{_esc(desc)}</desc>',
        f'  <rect width="{width}" height="{height}" rx="16" fill="{t.bg}"/>',
        f'  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="16" '
        f'fill="none" stroke="{t.border}"/>',
    ]


def _stacked_bar(rows: Rows, colors: list[str], t: Theme) -> list[str]:
    bar_x, bar_y, bar_w, bar_h = 28, 88, CARD_W - 56, 10
    out = [
        f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5" fill="{t.track}"/>',
        f'  <clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" '
        f'rx="5"/></clipPath>',
    ]
    x = float(bar_x)
    for (_, pct), color in zip(rows, colors):
        seg = bar_w * pct / 100.0
        if seg < 0.5:
            continue
        painted = max(seg, 2.0)  # keep tiny shares visible; clipPath trims overflow
        out.append(f'  <rect clip-path="url(#bar)" x="{x:.1f}" y="{bar_y}" width="{painted:.1f}" '
                   f'height="{bar_h}" fill="{color}"/>')
        x += painted
    return out


def render_card(title: str, subtitle: str, rows: Rows, t: Theme) -> str:
    """Render one language card as a self-contained SVG string."""
    colors = [t.other if name == "Other" else t.palette[i % len(t.palette)]
              for i, (name, _) in enumerate(rows)]
    desc = subtitle + ". " + ", ".join(f"{n} {format_pct(p)}" for n, p in rows)
    out = _frame(CARD_W, CARD_H, title, desc, t)
    out.append(f'  <text x="28" y="44" font-family="{SANS}" font-size="22" font-weight="700" '
               f'fill="{t.fg}">{_esc(title)}</text>')
    out.append(f'  <text x="28" y="68" font-family="{MONO}" font-size="14" fill="{t.muted}">'
               f'{_esc(subtitle)}</text>')
    out += _stacked_bar(rows, colors, t)
    row_y = 128
    for (name, pct), color in zip(rows, colors):
        out.append(f'  <circle cx="36" cy="{row_y - 6}" r="6" fill="{color}"/>')
        out.append(f'  <text x="54" y="{row_y}" font-family="{SANS}" font-size="17" '
                   f'fill="{t.fg}">{_esc(name)}</text>')
        out.append(f'  <text x="{CARD_W - 28}" y="{row_y}" text-anchor="end" font-family="{MONO}" '
                   f'font-size="17" fill="{t.muted}">{_esc(format_pct(pct))}</text>')
        row_y += 34
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _area_chart(cal: Calendar, t: Theme) -> list[str]:
    left, right, top, base = 400, ACT_W - 40, 52, 196
    n = len(cal.weeks)
    if n < 2:
        return [f'  <text x="{left}" y="{base}" font-family="{MONO}" font-size="16" '
                f'fill="{t.muted}">no calendar data</text>']
    peak = max(cal.weeks)
    scale = max(peak, 1)
    step = (right - left) / (n - 1)
    pts = [(left + i * step, base - (v / scale) * (base - top)) for i, v in enumerate(cal.weeks)]
    line = " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    out = [
        f'  <line x1="{left}" y1="{base}" x2="{right}" y2="{base}" stroke="{t.border}"/>',
        f'  <path d="M {pts[0][0]:.1f},{base} L {line} L {pts[-1][0]:.1f},{base} Z" '
        f'fill="{t.accent}" fill-opacity="0.14"/>',
        f'  <path d="M {line}" fill="none" stroke="{t.accent}" stroke-width="2.5" '
        f'stroke-linejoin="round" stroke-linecap="round"/>',
        f'  <circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="5" fill="{t.accent}"/>',
    ]
    for idx, label in month_ticks(cal.week_starts):
        out.append(f'  <text x="{pts[idx][0]:.1f}" y="{base + 26}" text-anchor="middle" '
                   f'font-family="{MONO}" font-size="15" fill="{t.muted}">{label}</text>')
    out.append(f'  <text x="{right}" y="{top - 14}" text-anchor="end" font-family="{MONO}" '
               f'font-size="14" fill="{t.muted}">peak {peak} / week</text>')
    return out


def render_activity(cal: Calendar, repos: int, stars: int, t: Theme) -> str:
    """Render the full-width contributions card."""
    desc = (f"{cal.total} contributions in the last 12 months across {repos} repositories "
            f"with {stars} stars; weekly trend chart")
    out = _frame(ACT_W, ACT_H, "Contributions, last 12 months", desc, t)
    out += [
        f'  <text x="40" y="48" font-family="{SANS}" font-size="22" font-weight="700" '
        f'fill="{t.fg}">Contributions</text>',
        f'  <text x="40" y="72" font-family="{MONO}" font-size="14" fill="{t.muted}">'
        f'last 12 months</text>',
        f'  <text x="38" y="152" font-family="{SANS}" font-size="72" font-weight="700" '
        f'letter-spacing="-2" fill="{t.accent}">{cal.total:,}</text>',
        f'  <text x="40" y="200" font-family="{SANS}" font-size="18" fill="{t.fg}">'
        f'{repos} repositories</text>',
        f'  <text x="40" y="226" font-family="{SANS}" font-size="18" fill="{t.fg}">'
        f'{stars} stars received</text>',
    ]
    out += _area_chart(cal, t)
    out.append("</svg>")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# GitHub API access
# --------------------------------------------------------------------------- #
class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    """Follow redirects but never forward the token to another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None and urllib.parse.urlsplit(newurl).hostname != API_HOST:
            new_req.remove_header("Authorization")
        return new_req


_OPENER = urllib.request.build_opener(_SameHostRedirect())


def _request(url: str, token: str, data: bytes | None = None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-cards",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with _OPENER.open(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _paged(url: str, token: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    sep = "&" if "?" in url else "?"
    for page in range(1, MAX_PAGES + 1):
        batch = _request(f"{url}{sep}per_page=100&page={page}", token)
        if not isinstance(batch, list):
            raise RuntimeError(f"unexpected payload for {url}: {type(batch).__name__}")
        items.extend(batch)
        if len(batch) < 100:
            return items
    raise RuntimeError(f"more than {MAX_PAGES} pages for {url}; refusing to continue")


def list_repos(user: str, token: str, include_private: bool) -> list[dict[str, Any]]:
    """Repositories owned by `user`, excluding forks and archived ones."""
    if not USERNAME_RE.match(user):
        raise ValueError(f"invalid GitHub username: {user!r}")
    if include_private:
        url = f"{API}/user/repos?affiliation=owner"
    else:
        url = f"{API}/users/{urllib.parse.quote(user, safe='')}/repos?type=owner"
    repos = _paged(url, token)
    return [r for r in repos
            if not r.get("fork") and not r.get("archived")
            and str(r.get("owner", {}).get("login", "")).casefold() == user.casefold()]


def repo_languages(full_name: str, token: str) -> dict[str, int]:
    """Language byte counts for one repository."""
    data = _request(f"{API}/repos/{full_name}/languages", token)
    if not isinstance(data, dict):
        raise RuntimeError(f"unexpected languages payload for {full_name}")
    return {str(k): int(v) for k, v in data.items()}


def fetch_contributions(user: str, token: str) -> dict[str, Any]:
    """Raw CONTRIB_QUERY response for the last 365 days."""
    now = dt.datetime.now(dt.timezone.utc)
    stamp = "%Y-%m-%dT%H:%M:%SZ"
    variables = {"login": user,
                 "from": (now - dt.timedelta(days=365)).strftime(stamp),
                 "to": now.strftime(stamp)}
    payload = json.dumps({"query": CONTRIB_QUERY, "variables": variables}).encode("utf-8")
    data = _request(f"{API}/graphql", token, payload)
    if (not isinstance(data, dict) or data.get("errors")
            or not (data.get("data") or {}).get("user")):
        raise RuntimeError(f"GraphQL error: {json.dumps(data)[:500]}")
    return data


# --------------------------------------------------------------------------- #
def _build(user: str, token: str, include_private: bool) -> dict[str, str]:
    repos = list_repos(user, token, include_private)
    by_bytes = aggregate_bytes([repo_languages(r["full_name"], token) for r in repos])
    rows_bytes = rank_with_other(merge_aliases(visible_only(by_bytes)))
    data = fetch_contributions(user, token)
    rows_commit = rank_with_other(merge_aliases(commit_weighted(parse_commit_buckets(data))))
    calendar = parse_calendar(data)
    if not repos or not rows_bytes or not rows_commit or not calendar.weeks:
        raise RuntimeError("no data returned; refusing to overwrite cards")
    stars = sum(int(r.get("stargazers_count", 0)) for r in repos)
    scope = "repos I own" if include_private else "public repos I own"
    cards: dict[str, str] = {}
    for name, t in THEMES.items():
        cards[f"activity-{name}.svg"] = render_activity(calendar, len(repos), stars, t)
        cards[f"languages-by-repo-{name}.svg"] = render_card(
            "Top languages by repo", f"code size across {len(repos)} {scope}", rows_bytes, t)
        cards[f"languages-by-commit-{name}.svg"] = render_card(
            "Top languages by commit", "my commits, last 12 months", rows_commit, t)
    return cards


def _build_with_fallback(user: str, token: str, profile_token: str,
                         github_token: str) -> dict[str, str]:
    """Build with PROFILE_TOKEN; on 401 (revoked/expired) retry public-only."""
    try:
        return _build(user, token, include_private=bool(profile_token))
    except urllib.error.HTTPError as err:
        if err.code != 401 or not profile_token or not github_token:
            raise
        print("warning: PROFILE_TOKEN was rejected (401); falling back to public scope. "
              "Update the repository secret to include private repositories again.",
              file=sys.stderr)
        return _build(user, github_token, include_private=False)


def main() -> int:
    # PROFILE_USER wins; USERNAME is kept for compatibility but note that Windows
    # sets USERNAME to the OS login, so always pass PROFILE_USER for local runs.
    user = (os.environ.get("PROFILE_USER") or os.environ.get("USERNAME", "")).strip()
    if not user:
        print("PROFILE_USER (or USERNAME) is required", file=sys.stderr)
        return 2
    profile_token = os.environ.get("PROFILE_TOKEN", "").strip()
    token = profile_token or os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("GITHUB_TOKEN or PROFILE_TOKEN is required", file=sys.stderr)
        return 2

    print(f"scope: {'private + public (PROFILE_TOKEN)' if profile_token else 'public only'}")
    try:
        cards = _build_with_fallback(user, token, profile_token,
                                     os.environ.get("GITHUB_TOKEN", "").strip())
    except urllib.error.HTTPError as err:
        print(f"GitHub API error {err.code} for {err.url}: {err.read()[:300]!r}", file=sys.stderr)
        return 1
    except (OSError, http.client.HTTPException, ValueError, RuntimeError, LookupError, TypeError) as err:
        print(f"build failed: {err!r}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, svg in cards.items():
        (OUT_DIR / name).write_text(svg, encoding="utf-8", newline="\n")
        print(f"wrote {OUT_DIR / name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
