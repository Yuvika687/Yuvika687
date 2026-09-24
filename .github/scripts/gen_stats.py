#!/usr/bin/env python3
"""Builds the live, data-driven SVGs (stats.svg, activity.svg) from the GitHub API.

Only real numbers are drawn. Needs GITHUB_TOKEN (provided by Actions, or `gh auth token` locally).
Usage: GITHUB_TOKEN=... python3 .github/scripts/gen_stats.py --user Yuvika687 --out dist
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_assets import CYAN, LAV, MINT, MONO, MUTED, PINK, TEXT, backdrop, border, e, svg  # noqa: E402

QUERY = """
query($login:String!){ user(login:$login){
  repositories(ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false, first:100){
    totalCount nodes{ name pushedAt primaryLanguage{ name } } }
  contributionsCollection{ contributionCalendar{ totalContributions
    weeks{ contributionDays{ date contributionCount } } } }
} }
"""


def call(url: str, token: str, body: dict | None = None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def streaks(days: list[tuple[dt.date, int]]) -> tuple[int, int]:
    days = sorted(days)
    longest = run = 0
    for _, n in days:
        run = run + 1 if n > 0 else 0
        longest = max(longest, run)
    today = dt.datetime.now(dt.timezone.utc).date()
    counts = {d: n for d, n in days}
    cur, d = 0, today
    if counts.get(d, 0) == 0:  # today may not have activity yet — don't break the streak
        d -= dt.timedelta(days=1)
    while counts.get(d, 0) > 0:
        cur += 1
        d -= dt.timedelta(days=1)
    return cur, longest


def ago(iso: str) -> str:
    t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    s = int((dt.datetime.now(dt.timezone.utc) - t).total_seconds())
    for n, u in ((86400, "d"), (3600, "h"), (60, "m")):
        if s >= n:
            return f"{s // n}{u} ago"
    return "just now"


def stats_svg(repos: int, total: int, cur: int, longest: int, langs: list[tuple[str, int]]) -> str:
    W, H = 1000, 300
    body = backdrop(W, H, seed=31, glow_a=(0.1, 0.2), glow_b=(0.9, 0.9))
    tiles = [("PUBLIC REPOS", repos, "original work", LAV), ("CONTRIBUTIONS", total, "last 12 months", PINK),
             ("CURRENT STREAK", cur, "days in a row", CYAN), ("LONGEST STREAK", longest, "days, past year", MINT)]
    for i, (label, val, sub, col) in enumerate(tiles):
        x = 34 + i * 240
        body += (
            f'<g transform="translate({x} 26)"><rect width="218" height="118" rx="16" fill="{col}" fill-opacity=".07" stroke="{col}" stroke-opacity=".45"/>'
            f'<text x="20" y="34" font-family="{MONO}" font-size="12" letter-spacing="2.5" fill="{col}">{label}</text>'
            f'<text x="20" y="86" font-size="46" font-weight="800" fill="{TEXT}">{val:,}'
            f'<animate attributeName="opacity" values="0;1" dur=".9s" begin="{i*0.15}s" fill="freeze"/></text>'
            f'<text x="20" y="106" font-family="{MONO}" font-size="12" fill="{MUTED}">{sub}</text></g>'
        )
    body += f'<text x="34" y="182" font-family="{MONO}" font-size="12" letter-spacing="2.5" fill="{MUTED}">PRIMARY LANGUAGE ACROSS MY PUBLIC REPOS</text>'
    tot = sum(n for _, n in langs) or 1
    palette = [LAV, PINK, CYAN, MINT, "#FBBF24", "#C4B5FD"]
    x, bw = 34, 932
    body += f'<clipPath id="lb"><rect x="{x}" y="196" width="{bw}" height="16" rx="8"/></clipPath><g clip-path="url(#lb)">'
    cx = x
    for i, (name, n) in enumerate(langs):
        w = bw * n / tot
        body += (
            f'<rect x="{cx:.1f}" y="196" width="{w:.1f}" height="16" fill="{palette[i % len(palette)]}">'
            f'<animate attributeName="width" values="0;{w:.1f}" dur="1.1s" begin="{i*0.12}s" fill="freeze"/></rect>'
        )
        cx += w
    body += "</g>"
    lx = 34
    for i, (name, n) in enumerate(langs):
        label = f"{name}  ·  {n}"
        body += (
            f'<circle cx="{lx+6}" cy="244" r="5" fill="{palette[i % len(palette)]}"/>'
            f'<text x="{lx+18}" y="249" font-size="14" font-weight="600" fill="{TEXT}">{e(name)}'
            f'<tspan font-family="{MONO}" font-weight="400" font-size="12.5" fill="{MUTED}">  ·  {n}</tspan></text>'
        )
        lx += 44 + len(label) * 8.2
    body += border(W, H)
    return svg(W, H, body)


def activity_svg(weeks: list[int], pushes: list[tuple[str, str, str]], stamp: str) -> str:
    W, H = 1000, 300
    body = backdrop(W, H, seed=32, glow_a=(0.15, 0.7), glow_b=(0.9, 0.2))
    X0, X1, Y1, YH = 40, 590, 230, 150
    peak = max(weeks) or 1
    pts = [(X0 + (X1 - X0) * i / max(len(weeks) - 1, 1), Y1 - YH * (v / peak)) for i, v in enumerate(weeks)]
    line = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    area = line + f" L{X1} {Y1} L{X0} {Y1} Z"
    body += (
        f'<defs><linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{PINK}" stop-opacity=".45"/>'
        f'<stop offset="1" stop-color="{LAV}" stop-opacity="0"/></linearGradient></defs>'
        f'<text x="40" y="44" font-family="{MONO}" font-size="12" letter-spacing="2.5" fill="{MUTED}">CONTRIBUTIONS PER WEEK · LAST 12 MONTHS</text>'
        f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="{LAV}" stroke-opacity=".3"/>'
        f'<path d="{area}" fill="url(#ar)"/>'
        f'<path d="{line}" fill="none" stroke="url(#g)" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="0">'
        f'<animate attributeName="stroke-dashoffset" values="1;0" dur="2.2s" fill="freeze"/></path>'
        f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="5" fill="{CYAN}"><animate attributeName="r" values="5;9;5" dur="2s" repeatCount="indefinite"/></circle>'
        f'<text x="{X0}" y="{Y1+26}" font-family="{MONO}" font-size="12" fill="{MUTED}">52 weeks ago</text>'
        f'<text x="{X1}" y="{Y1+26}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{MUTED}">this week</text>'
    )
    body += f'<line x1="640" y1="34" x2="640" y2="266" stroke="{LAV}" stroke-opacity=".2" stroke-dasharray="2 6"/>'
    body += f'<text x="670" y="44" font-family="{MONO}" font-size="12" letter-spacing="2.5" fill="{MUTED}">RECENT PUSHES</text>'
    for i, (repo, msg, when) in enumerate(pushes[:4]):
        y = 84 + i * 46
        msg = msg if len(msg) <= 34 else msg[:33] + "…"
        body += (
            f'<circle cx="676" cy="{y-4}" r="4" fill="{PINK if i == 0 else LAV}"/>'
            f'<text x="692" y="{y}" font-family="{MONO}" font-size="14" font-weight="700" fill="{PINK}">{e(repo)}</text>'
            f'<text x="960" y="{y}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{MUTED}">{e(when)}</text>'
            f'<text x="692" y="{y+19}" font-size="14" fill="{TEXT}" fill-opacity=".85">{e(msg)}</text>'
        )
    body += f'<text x="960" y="284" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}" fill-opacity=".7">updated {e(stamp)}</text>'
    body += border(W, H)
    return svg(W, H, body)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="Yuvika687")
    ap.add_argument("--out", default="dist")
    a = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is required")

    u = call("https://api.github.com/graphql", token, {"query": QUERY, "variables": {"login": a.user}})["data"]["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [(dt.date.fromisoformat(d["date"]), d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    cur, longest = streaks(days)
    weekly = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]

    counts: dict[str, int] = {}
    for r in u["repositories"]["nodes"]:
        if r["primaryLanguage"]:
            counts[r["primaryLanguage"]["name"]] = counts.get(r["primaryLanguage"]["name"], 0) + 1
    langs = sorted(counts.items(), key=lambda t: -t[1])[:6]

    recent = sorted(u["repositories"]["nodes"], key=lambda r: r["pushedAt"] or "", reverse=True)[:6]
    found = []
    for r in recent:
        try:
            cs = call(f"https://api.github.com/repos/{a.user}/{r['name']}/commits?per_page=2&author={a.user}", token)
        except Exception:
            continue
        for c in cs:
            found.append((c["commit"]["author"]["date"], r["name"], c["commit"]["message"].splitlines()[0]))
    found.sort(reverse=True)
    pushes = [(repo, msg, ago(when)) for when, repo, msg in found[:5]]

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    (out / "stats.svg").write_text(stats_svg(u["repositories"]["totalCount"], cal["totalContributions"], cur, longest, langs), encoding="utf-8")
    (out / "activity.svg").write_text(activity_svg(weekly[-52:], pushes, stamp), encoding="utf-8")
    print(f"repos={u['repositories']['totalCount']} contributions={cal['totalContributions']} streak={cur}/{longest} langs={langs} pushes={len(pushes)}")


if __name__ == "__main__":
    main()
