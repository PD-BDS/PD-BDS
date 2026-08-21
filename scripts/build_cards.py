#!/usr/bin/env python3
"""Build the language cards shown on the profile README.

Pulls language data from the GitHub API, aggregates it two ways (bytes across
repositories, and commit-weighted over the last year), and renders two SVG
cards into assets/readme/. Notebook and generated-markup languages listed in
HIDDEN are left out so the cards reflect hand-written code.

Environment:
    USERNAME       GitHub login to build cards for (required)
    GITHUB_TOKEN   Token for API calls; the Actions default token is enough
                   for public repositories
    PROFILE_TOKEN  Optional personal token with `repo` scope; when set, private
                   repositories are included too
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
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
PALETTE = ("#58A6FF", "#3FB950", "#D29922", "#A371F7", "#F778BA")
OTHER_COLOR = "#6E7681"

CARD_W, CARD_H = 480, 290
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

LANGS_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
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


# --------------------------------------------------------------------------- #
# Pure data helpers (unit-tested)
# --------------------------------------------------------------------------- #
def aggregate_bytes(language_maps: list[Mapping[str, int]]) -> dict[str, int]:
    """Sum language bytes across repositories."""
    totals: dict[str, int] = {}
    for langs in language_maps:
        for name, size in langs.items():
            totals[name] = totals.get(name, 0) + int(size)
    return totals


def commit_weighted(repos: list[tuple[int, Mapping[str, int]]],
                    hidden: frozenset[str] = HIDDEN) -> dict[str, float]:
    """Spread each repository's commit count across its visible languages.

    Each repository contributes `commits * share_of_language` to a language,
    where shares are computed over the repository's visible languages only.
    """
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


def rank_with_other(totals: Mapping[str, float], top_n: int = TOP_N) -> Rows:
    """Return [(name, percent), ...] for the top_n languages plus an 'Other' row.

    Percentages sum to 100 (up to rounding). 'Other' is omitted when empty.
    """
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


def _card_header(title: str, subtitle: str, rows: Rows) -> list[str]:
    desc = _esc(subtitle) + ". " + _esc(", ".join(f"{n} {format_pct(p)}" for n, p in rows))
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" '
        f'viewBox="0 0 {CARD_W} {CARD_H}" role="img" aria-labelledby="t d">',
        f'  <title id="t">{_esc(title)}</title>',
        f'  <desc id="d">{desc}</desc>',
        f'  <rect width="{CARD_W}" height="{CARD_H}" rx="20" fill="#0B0F14"/>',
        f'  <rect x="0.5" y="0.5" width="{CARD_W - 1}" height="{CARD_H - 1}" rx="20" '
        f'fill="none" stroke="#1F2A37"/>',
        f'  <text x="28" y="44" font-family="{SANS}" font-size="22" font-weight="700" '
        f'fill="#E6EDF3">{_esc(title)}</text>',
        f'  <text x="28" y="68" font-family="{MONO}" font-size="14" fill="#8B949E">'
        f'{_esc(subtitle)}</text>',
    ]


def _stacked_bar(rows: Rows, colors: list[str]) -> list[str]:
    bar_x, bar_y, bar_w, bar_h = 28, 88, CARD_W - 56, 10
    out = [
        f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5" fill="#21262D"/>',
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


def render_card(title: str, subtitle: str, rows: Rows) -> str:
    """Render one language card as a self-contained SVG string."""
    colors = [OTHER_COLOR if name == "Other" else PALETTE[i % len(PALETTE)]
              for i, (name, _) in enumerate(rows)]
    out = _card_header(title, subtitle, rows) + _stacked_bar(rows, colors)
    row_y = 128
    for (name, pct), color in zip(rows, colors):
        out.append(f'  <circle cx="36" cy="{row_y - 6}" r="6" fill="{color}"/>')
        out.append(f'  <text x="54" y="{row_y}" font-family="{SANS}" font-size="17" '
                   f'fill="#C9D1D9">{_esc(name)}</text>')
        out.append(f'  <text x="{CARD_W - 28}" y="{row_y}" text-anchor="end" font-family="{MONO}" '
                   f'font-size="17" fill="#8B949E">{_esc(format_pct(pct))}</text>')
        row_y += 34
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
    """Owner repositories of `user`, excluding forks and archived ones."""
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


def commit_contributions(user: str, token: str) -> list[tuple[int, dict[str, int]]]:
    """(commit count, language bytes) per repository committed to in the last year."""
    now = dt.datetime.now(dt.timezone.utc)
    stamp = "%Y-%m-%dT%H:%M:%SZ"
    variables = {"login": user,
                 "from": (now - dt.timedelta(days=365)).strftime(stamp),
                 "to": now.strftime(stamp)}
    payload = json.dumps({"query": LANGS_QUERY, "variables": variables}).encode("utf-8")
    data = _request(f"{API}/graphql", token, payload)
    if not isinstance(data, dict) or data.get("errors") or not data.get("data"):
        raise RuntimeError(f"GraphQL error: {json.dumps(data)[:500]}")
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


# --------------------------------------------------------------------------- #
def _build(user: str, token: str, include_private: bool) -> dict[str, str]:
    repos = list_repos(user, token, include_private)
    by_bytes = aggregate_bytes([repo_languages(r["full_name"], token) for r in repos])
    rows_bytes = rank_with_other(visible_only(by_bytes))
    rows_commit = rank_with_other(commit_weighted(commit_contributions(user, token)))
    if not repos or not rows_bytes or not rows_commit:
        raise RuntimeError("no language data returned; refusing to overwrite cards")
    scope = "public and private repos" if include_private else "public repos"
    return {
        "languages-by-repo.svg": render_card(
            "Top languages by repo", f"code size across {len(repos)} {scope}", rows_bytes),
        "languages-by-commit.svg": render_card(
            "Top languages by commit", "commits over the last 12 months", rows_commit),
    }


def main() -> int:
    user = os.environ.get("USERNAME", "").strip()
    if not user:
        print("USERNAME is required", file=sys.stderr)
        return 2
    profile_token = os.environ.get("PROFILE_TOKEN", "").strip()
    token = profile_token or os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("GITHUB_TOKEN or PROFILE_TOKEN is required", file=sys.stderr)
        return 2

    try:
        cards = _build(user, token, include_private=bool(profile_token))
    except urllib.error.HTTPError as err:
        print(f"GitHub API error {err.code} for {err.url}: {err.read()[:300]!r}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, ValueError, RuntimeError, KeyError, TypeError) as err:
        print(f"build failed: {err!r}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, svg in cards.items():
        (OUT_DIR / name).write_text(svg, encoding="utf-8", newline="\n")
        print(f"wrote {OUT_DIR / name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
