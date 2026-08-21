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
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.github.com"
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "readme"

HIDDEN = frozenset({"Jupyter Notebook", "HTML", "CSS", "Mako", "SCSS"})
TOP_N = 4  # ranked rows before everything else is folded into "Other"
PALETTE = ("#58A6FF", "#3FB950", "#D29922", "#A371F7", "#F778BA")
OTHER_COLOR = "#6E7681"

CARD_W, CARD_H = 480, 290
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


# --------------------------------------------------------------------------- #
# Pure data helpers (unit-tested)
# --------------------------------------------------------------------------- #
def aggregate_bytes(language_maps: list[dict[str, int]]) -> dict[str, int]:
    """Sum language bytes across repositories."""
    totals: dict[str, int] = {}
    for langs in language_maps:
        for name, size in langs.items():
            totals[name] = totals.get(name, 0) + int(size)
    return totals


def commit_weighted(repos: list[tuple[int, dict[str, int]]],
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


def visible_only(totals: dict[str, float], hidden: frozenset[str] = HIDDEN) -> dict[str, float]:
    return {k: v for k, v in totals.items() if k not in hidden and v > 0}


def rank_with_other(totals: dict[str, float], top_n: int = TOP_N) -> list[tuple[str, float]]:
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
    if pct >= 10:
        return f"{pct:.1f}%"
    if pct >= 0.1:
        return f"{pct:.1f}%"
    return "<0.1%"


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_card(title: str, subtitle: str, rows: list[tuple[str, float]]) -> str:
    """Render one language card as a self-contained SVG string."""
    sans = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    mono = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
    colors = [OTHER_COLOR if name == "Other" else PALETTE[i % len(PALETTE)]
              for i, (name, _) in enumerate(rows)]

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" '
        f'viewBox="0 0 {CARD_W} {CARD_H}" role="img" aria-labelledby="t d">',
        f"  <title id=\"t\">{_esc(title)}</title>",
        f"  <desc id=\"d\">{_esc(subtitle)}. " +
        _esc(", ".join(f"{n} {format_pct(p)}" for n, p in rows)) + "</desc>",
        f'  <rect width="{CARD_W}" height="{CARD_H}" rx="20" fill="#0B0F14"/>',
        f'  <rect x="0.5" y="0.5" width="{CARD_W - 1}" height="{CARD_H - 1}" rx="20" fill="none" stroke="#1F2A37"/>',
        f'  <text x="28" y="44" font-family="{sans}" font-size="22" font-weight="700" fill="#E6EDF3">{_esc(title)}</text>',
        f'  <text x="28" y="68" font-family="{mono}" font-size="14" fill="#8B949E">{_esc(subtitle)}</text>',
    ]

    # Stacked bar
    bar_x, bar_y, bar_w, bar_h = 28, 88, CARD_W - 56, 10
    out.append(f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5" fill="#21262D"/>')
    out.append(f'  <clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5"/></clipPath>')
    x = float(bar_x)
    for (_, pct), color in zip(rows, colors):
        seg = bar_w * pct / 100.0
        if seg >= 0.5:
            out.append(f'  <rect clip-path="url(#bar)" x="{x:.1f}" y="{bar_y}" width="{max(seg, 2):.1f}" '
                       f'height="{bar_h}" fill="{color}"/>')
        x += seg

    # Ranked rows
    row_y = 128
    for (name, pct), color in zip(rows, colors):
        out.append(f'  <circle cx="36" cy="{row_y - 6}" r="6" fill="{color}"/>')
        out.append(f'  <text x="54" y="{row_y}" font-family="{sans}" font-size="17" fill="#C9D1D9">{_esc(name)}</text>')
        out.append(f'  <text x="{CARD_W - 28}" y="{row_y}" text-anchor="end" font-family="{mono}" '
                   f'font-size="17" fill="#8B949E">{format_pct(pct)}</text>')
        row_y += 34

    out.append("</svg>")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# GitHub API access
# --------------------------------------------------------------------------- #
def _request(url: str, token: str, data: bytes | None = None) -> object:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-cards"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _paged(url: str, token: str) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        sep = "&" if "?" in url else "?"
        batch = _request(f"{url}{sep}per_page=100&page={page}", token)
        if not isinstance(batch, list) or not batch:
            return items
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


def list_repos(user: str, token: str, include_private: bool) -> list[dict]:
    url = f"{API}/user/repos?affiliation=owner" if include_private else f"{API}/users/{user}/repos?type=owner"
    repos = _paged(url, token)
    return [r for r in repos if not r.get("fork") and not r.get("archived")]


def repo_languages(full_name: str, token: str) -> dict[str, int]:
    data = _request(f"{API}/repos/{full_name}/languages", token)
    return data if isinstance(data, dict) else {}


def commit_contributions(user: str, token: str) -> list[tuple[int, dict[str, int]]]:
    now = dt.datetime.now(dt.timezone.utc)
    variables = {"login": user,
                 "from": (now - dt.timedelta(days=365)).isoformat(timespec="seconds"),
                 "to": now.isoformat(timespec="seconds")}
    payload = json.dumps({"query": LANGS_QUERY, "variables": variables}).encode("utf-8")
    data = _request(f"{API}/graphql", token, payload)
    if not isinstance(data, dict) or data.get("errors"):
        raise RuntimeError(f"GraphQL error: {json.dumps(data)[:500]}")
    buckets = data["data"]["user"]["contributionsCollection"]["commitContributionsByRepository"]
    result: list[tuple[int, dict[str, int]]] = []
    for b in buckets:
        repo = b["repository"]
        if repo.get("isFork"):
            continue
        langs = {e["node"]["name"]: int(e["size"]) for e in repo["languages"]["edges"]}
        result.append((int(b["contributions"]["totalCount"]), langs))
    return result


# --------------------------------------------------------------------------- #
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
        repos = list_repos(user, token, include_private=bool(profile_token))
        by_bytes = aggregate_bytes([repo_languages(r["full_name"], token) for r in repos])
        by_commit = commit_weighted(commit_contributions(user, token))
    except urllib.error.HTTPError as err:
        print(f"GitHub API error {err.code} for {err.url}: {err.read()[:300]!r}", file=sys.stderr)
        return 1

    scope = "public and private repos" if profile_token else "public repos"
    cards = {
        "languages-by-repo.svg": render_card(
            "Top languages by repo", f"code size across {len(repos)} {scope}",
            rank_with_other(visible_only(by_bytes))),
        "languages-by-commit.svg": render_card(
            "Top languages by commit", "commits over the last 12 months",
            rank_with_other(by_commit)),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, svg in cards.items():
        (OUT_DIR / name).write_text(svg, encoding="utf-8", newline="\n")
        print(f"wrote {OUT_DIR / name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
