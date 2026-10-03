#!/usr/bin/env python3
"""Command Center README assets ("the Trailer").

Two modes, standard library only:

  static  Hand-designed, animated SVGs that only change when this file changes:
          hero (dark + light), launch button, profile card, tech-stack card.
            python3 .github/scripts/command_center.py static --out assets/cc

  live    Data-driven SVGs rebuilt by the profile-build Action and published to the `output` branch,
          plus the project link list between the README markers (only if the README has them):
            GITHUB_TOKEN=... python3 .github/scripts/command_center.py live --user Yuvika687 --out dist --readme README.md

Nothing project-related is hardcoded: repos, the featured project and every number come from the GitHub API.
Eligibility mirrors the website: no forks, archived, empty or profile repos, and nothing tagged `hide-from-portfolio`;
pinned repos first, then most recently pushed; the `featured` / `now-building` topic picks the Now Building card.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import math
import os
import pathlib
import random
import re
import sys
import urllib.request
from xml.sax.saxutils import escape

# ── identity & palette (mirrors the website's data/profile.ts and design tokens) ─────────────────────────────
SITE = "https://yuvika-command-center.vercel.app"
NAME = "Yuvika Malhotra"
ROLE = "B.Tech CSE (AI/ML) | 2027"
LOCATION = "Punjab, India"
TAGLINE = "Student • Builder • Learner • Tech Explorer"
BIO = "Final-year CSE student specialising in AI & ML. I build computer-vision pipelines, LLM systems and full-stack apps."
FOCUS = ["Computer Vision", "LLM Systems", "Full-Stack AI Apps", "Open Source"]
LINKEDIN = "linkedin.com/in/yuvikamalhotra"
EMAIL = "yuvikamalhotra1414@gmail.com"
SKILLS = [
    ("LANGUAGES", [("Python", "#3776AB"), ("C++", "#00599C"), ("C", "#A8B9CC"), ("SQL", "#22D3EE"), ("JavaScript", "#F7DF1E"), ("HTML & CSS", "#E34F26")]),
    ("AI / ML", [("PyTorch", "#EE4C2C"), ("OpenCV", "#5C3EE8"), ("Scikit-learn", "#F7931E"), ("XGBoost", "#189FDD"), ("LightGBM", "#9ACD32"),
                 ("CatBoost", "#FFCC00"), ("Hugging Face", "#FFD21E"), ("NumPy", "#4DABCF"), ("Pandas", "#E70488")]),
    ("BACKEND & APPS", [("FastAPI", "#009688"), ("Flask", "#E5E7FF"), ("Streamlit", "#FF4B4B"), ("SQLAlchemy", "#D71F00"), ("JWT", "#E5E7FF")]),
    ("DATABASES", [("PostgreSQL", "#4169E1"), ("MySQL", "#4479A1"), ("SQLite", "#4FA3D8")]),
    ("TOOLS", [("Git", "#F05032"), ("GitHub", "#E5E7FF"), ("Linux", "#FCC624")]),
]

BASE, NAVY = "#05060F", "#0B0D1F"
VIOLET, PURPLE, BLUE, PINK, CYAN, GREEN = "#8B5CF6", "#A855F7", "#3B82F6", "#EC4899", "#22D3EE", "#22C55E"
INK, DIM = "#E5E7FF", "#9CA3C7"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Helvetica Neue',Arial,sans-serif"
MONO = "'JetBrains Mono','SF Mono','Cascadia Code',Menlo,Consolas,monospace"

# Topic → (label, colour). Unknown topics fall back to the raw topic in violet.
TECH = {
    "python": ("Python", "#3776AB"), "javascript": ("JavaScript", "#F7DF1E"), "typescript": ("TypeScript", "#3178C6"), "cpp": ("C++", "#00599C"),
    "html": ("HTML", "#E34F26"), "css": ("CSS", "#663399"), "jupyter-notebook": ("Jupyter", "#F37626"), "pytorch": ("PyTorch", "#EE4C2C"),
    "opencv": ("OpenCV", "#5C3EE8"), "scikit-learn": ("scikit-learn", "#F7931E"), "xgboost": ("XGBoost", "#189FDD"), "lightgbm": ("LightGBM", "#9ACD32"),
    "catboost": ("CatBoost", "#FFCC00"), "huggingface": ("Hugging Face", "#FFD21E"), "fastapi": ("FastAPI", "#009688"), "streamlit": ("Streamlit", "#FF4B4B"),
    "nextjs": ("Next.js", INK), "postgresql": ("PostgreSQL", "#4169E1"), "docker": ("Docker", "#2496ED"), "jwt": ("JWT", INK), "mediapipe": ("MediaPipe", "#0097A7"),
    "gemini": ("Gemini", "#8E75B2"), "pandas": ("Pandas", "#E70488"), "llm": ("LLM", PINK), "computer-vision": ("Computer Vision", PURPLE),
    "machine-learning": ("Machine Learning", VIOLET), "full-stack": ("Full-stack", BLUE), "chrome-extension": ("Chrome Extension", "#4285F4"),
    "spaced-repetition": ("Spaced Repetition", CYAN), "unsupervised-learning": ("Unsupervised Learning", VIOLET), "pose-estimation": ("Pose Estimation", CYAN),
}

HIDE_TOPIC = "hide-from-portfolio"
FEATURE_TOPICS = {"featured", "now-building"}


def e(s: str) -> str:
    return escape(str(s), {'"': "&quot;"})


def clip(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def wrap(text: str, width: int, lines: int) -> list[str]:
    words, out, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur = f"{cur} {w}" if cur else w
        else:
            out.append(cur)
            cur = w
            if len(out) == lines:
                break
    if len(out) < lines and cur:
        out.append(cur)
    if len(out) == lines and " ".join(out) != " ".join(words):
        out[-1] = clip(out[-1] + " …", width)
    return out


def svg(w: int, h: int, body: str, defs: str = "", title: str = "") -> str:
    t = f"<title>{e(title)}</title>" if title else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'font-family="{SANS}" role="img">{t}<defs>{defs}'
        f'<linearGradient id="vp" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
        f'<linearGradient id="vb" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{VIOLET}" stop-opacity=".7"/><stop offset=".5" stop-color="{BLUE}" stop-opacity=".25"/>'
        f'<stop offset="1" stop-color="{VIOLET}" stop-opacity=".12"/></linearGradient>'
        f"</defs>{body}</svg>"
    )


def panel(w: int, h: int, r: int = 22) -> str:
    """Glass card: navy fill, violet→blue hairline border, faint top highlight."""
    return (
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{r}" fill="{NAVY}"/>'
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{r}" fill="url(#vb)" fill-opacity=".06"/>'
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{r}" fill="none" stroke="url(#vb)" stroke-width="1.2"/>'
        f'<line x1="{w*0.15:.0f}" x2="{w*0.85:.0f}" y1="1.5" y2="1.5" stroke="#fff" stroke-opacity=".14"/>'
    )


def label(x: float, y: float, text: str, color: str = DIM, size: int = 13, anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" letter-spacing="2.6" fill="{color}" text-anchor="{anchor}">{e(text)}</text>'


def chip(x: float, y: float, text: str, color: str, size: int = 15) -> tuple[str, float]:
    w = len(text) * size * 0.56 + 34
    return (
        f'<g transform="translate({x:.0f} {y:.0f})"><rect width="{w:.0f}" height="{size+15}" rx="8" fill="{color}" fill-opacity=".09" stroke="{color}" stroke-opacity=".45"/>'
        f'<circle cx="14" cy="{(size+15)/2:.1f}" r="4" fill="{color}"/>'
        f'<text x="25" y="{size+15 - (size+15-size*0.72)/2:.1f}" font-size="{size}" fill="{INK}">{e(text)}</text></g>',
        w,
    )


# ── scenery ─────────────────────────────────────────────────────────────────────────────────────────────────────
def ridge(seed: int, w: int, horizon: float, base: float, amp: float, envelope=lambda x: 1.0, sharp: float = 0.6) -> str:
    rnd = random.Random(seed)
    layers = []
    for o in range(5):
        cells = 3 * 2**o
        layers.append((cells, 1 / 1.9**o, [rnd.random() for _ in range(cells + 2)]))

    def sample(t: float) -> float:
        v = norm = 0.0
        for cells, weight, vals in layers:
            p = t * cells
            i = int(p)
            f = p - i
            s = f * f * (3 - 2 * f)
            v += (vals[i] * (1 - s) + vals[i + 1] * s) * weight
            norm += weight
        n = v / norm
        return n * (1 - sharp) + (1 - abs(2 * n - 1)) * sharp

    pts = [f"M -20 {horizon}"]
    for x in range(-20, w + 21, 6):
        t = (x + 20) / (w + 40)
        y = base - amp * sample(t) ** 2.2 * envelope(x)
        pts.append(f"L {x} {y:.1f}")
    pts.append(f"L {w+20} {horizon} Z")
    return " ".join(pts)


def landscape(w: int, h: int, horizon: int, light: bool, moon=(0.0, 0.0, 0.0), seed: int = 7) -> tuple[str, str]:
    """Night (or dawn) scene: sky, nebula, twinkling stars, glowing crescent, three ridges, lake reflection, haze."""
    mx, my, mr = moon
    sky = ("#F5F3FF", "#E9E5FF", "#D8CCFB") if light else (BASE, NAVY, "#1A1040")
    ridges = (
        [("#C4B5FD", "#8B5CF6"), ("#A78BFA", "#3B82F6"), ("#7C3AED", "#EC4899")]
        if light
        else [("#3B2A7A", "#A78BFA"), ("#24175A", "#3B82F6"), ("#140F33", "#EC4899")]
    )
    clear = lambda x: 1 - 0.55 * math.exp(-(((x - mx) / 170) ** 2))
    paths = [
        ridge(seed + 4, w, horizon, horizon - 4, h * 0.62, lambda x: clear(x) * (0.75 + 0.25 * math.sin(x / 200))),
        ridge(seed + 16, w, horizon, horizon - 2, h * 0.42, lambda x: clear(x) * 0.95, 0.7),
        ridge(seed + 30, w, horizon, horizon, h * 0.2, lambda x: 0.55 + 0.45 * abs(math.sin(x / 320)), 0.5),
    ]
    defs = (
        f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{sky[0]}"/><stop offset=".55" stop-color="{sky[1]}"/>'
        f'<stop offset="1" stop-color="{sky[2]}"/></linearGradient>'
        f'<radialGradient id="neb1"><stop offset="0" stop-color="{VIOLET}" stop-opacity="{.22 if light else .38}"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="neb2"><stop offset="0" stop-color="{BLUE}" stop-opacity="{.14 if light else .26}"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="neb3"><stop offset="0" stop-color="{PINK}" stop-opacity=".16"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="mglow"><stop offset="0" stop-color="#C4B5FD" stop-opacity=".6"/><stop offset=".4" stop-color="{VIOLET}" stop-opacity=".2"/>'
        f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="msurf" cx=".35" cy=".4"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".6" stop-color="#EDE9FE"/><stop offset="1" stop-color="#C4B5FD"/></radialGradient>'
        f'<mask id="cres"><circle cx="{mx}" cy="{my}" r="{mr}" fill="#fff"/><circle cx="{mx + mr*0.42:.1f}" cy="{my - mr*0.18:.1f}" r="{mr*0.9:.1f}" fill="#000"/></mask>'
        f'<linearGradient id="water" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{sky[2] if light else NAVY}" stop-opacity=".3"/>'
        f'<stop offset="1" stop-color="{sky[1] if light else BASE}" stop-opacity=".92"/></linearGradient>'
    )
    for i, (top, _) in enumerate(ridges):
        bottom = sky[1] if light else BASE
        defs += f'<linearGradient id="rf{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>'

    rnd = random.Random(seed)
    stars = ""
    if not light:
        for _ in range(int(w * horizon / 1800)):
            x, y = rnd.random() * w, rnd.random() ** 1.4 * (horizon - 30)
            r = 0.5 + rnd.random() ** 3 * 1.4
            d = 2.5 + rnd.random() * 4
            stars += (
                f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.2f}" fill="#E5E7FF" opacity=".8">'
                f'<animate attributeName="opacity" values=".9;.25;.9" dur="{d:.1f}s" begin="{rnd.random()*4:.1f}s" repeatCount="indefinite"/></circle>'
            )
    ridge_svg = ""
    for i, p in enumerate(paths):
        rim = ridges[i][1]
        ridge_svg += (
            f'<path d="{p}" fill="url(#rf{i})"/><path d="{p}" fill="none" stroke="{rim}" stroke-width="5" stroke-opacity=".12"/>'
            f'<path d="{p}" fill="none" stroke="{rim}" stroke-width="1.1" stroke-opacity=".8"/>'
        )
    shimmer = "".join(
        f'<rect x="{mx - (10 + i*4.5)/2 + rnd.uniform(-14, 14):.0f}" y="{horizon + 5 + i*i*0.55:.0f}" width="{10 + i*4.5 + rnd.random()*24:.0f}" height="1.4" rx=".7" '
        f'fill="#DDD6FE" opacity="{max(0.06, 0.55 - i*0.03):.2f}"/>'
        for i in range(16)
        if horizon + 5 + i * i * 0.55 < h
    )
    body = (
        f'<rect width="{w}" height="{h}" fill="url(#sky)"/>'
        f'<ellipse cx="{w*0.28:.0f}" cy="{h*0.3:.0f}" rx="{w*0.36:.0f}" ry="{h*0.32:.0f}" fill="url(#neb1)" transform="rotate(-12 {w*0.28:.0f} {h*0.3:.0f})"/>'
        f'<ellipse cx="{w*0.55:.0f}" cy="{h*0.42:.0f}" rx="{w*0.32:.0f}" ry="{h*0.22:.0f}" fill="url(#neb2)"/>'
        f'<ellipse cx="{w*0.45:.0f}" cy="{h*0.22:.0f}" rx="{w*0.2:.0f}" ry="{h*0.14:.0f}" fill="url(#neb3)">'
        f'<animateTransform attributeName="transform" type="translate" values="-40 0;50 0;-40 0" dur="60s" repeatCount="indefinite"/></ellipse>'
        f"{stars}"
        f'<circle cx="{mx}" cy="{my}" r="{mr*3.6:.0f}" fill="url(#mglow)"><animate attributeName="opacity" values=".75;1;.75" dur="8s" repeatCount="indefinite"/></circle>'
        f'<circle cx="{mx}" cy="{my}" r="{mr}" fill="url(#msurf)" mask="url(#cres)"/>'
        f"{ridge_svg}"
        f'<g transform="translate(0 {horizon*2}) scale(1 -1)" opacity=".38">{ridge_svg}</g>'
        f'<rect y="{horizon}" width="{w}" height="{h-horizon}" fill="url(#water)"/>'
        f'<line x1="0" x2="{w}" y1="{horizon+.5}" y2="{horizon+.5}" stroke="#C4B5FD" stroke-opacity=".45"/>'
        f'<g>{shimmer}<animate attributeName="opacity" values="1;.5;1" dur="4.5s" repeatCount="indefinite"/></g>'
    )
    return defs, body


# ── static assets ───────────────────────────────────────────────────────────────────────────────────────────────
def hero(light: bool) -> str:
    W, H, HORIZON = 1200, 400, 318
    defs, scene = landscape(W, H, HORIZON, light, moon=(1080, 92, 44))
    ink = "#1E1B4B" if light else INK
    dim = "#4C4A7A" if light else DIM
    lines = [("&gt; initializing portfolio...", "ok"), ("&gt; loading AI/ML modules...", "ok"), ("&gt; cybersecurity systems: active", ""), ("&gt; status: building...", "")]
    term = (
        f'<g transform="translate(640 74)">'
        f'<rect width="380" height="196" rx="16" fill="{BASE}" fill-opacity=".82" stroke="url(#vb)" stroke-width="1.2"/>'
        f'<circle cx="22" cy="22" r="6" fill="#FF5F57"/><circle cx="42" cy="22" r="6" fill="#FEBC2E"/><circle cx="62" cy="22" r="6" fill="#28C840"/>'
        f'<text x="190" y="27" text-anchor="middle" font-family="{MONO}" font-size="13" fill="{DIM}">yuvika@dev: ~</text>'
        f'<line x1="0" x2="380" y1="44" y2="44" stroke="#fff" stroke-opacity=".07"/>'
    )
    LOOP = 10
    for i, (text, status) in enumerate(lines):
        y = 80 + i * 32
        t0, t1 = (0.4 + i * 1.5) / LOOP, (1.5 + i * 1.5) / LOOP
        defs += (
            f'<clipPath id="ty{i}"><rect x="18" y="{y-18}" height="26" width="0">'
            f'<animate attributeName="width" values="0;0;345;345" keyTimes="0;{t0:.3f};{t1:.3f};1" dur="{LOOP}s" repeatCount="indefinite"/></rect></clipPath>'
        )
        term += (
            f'<g clip-path="url(#ty{i})"><text x="20" y="{y}" font-family="{MONO}" font-size="15" fill="{GREEN if i == 3 else INK}">{text}'
            + (f'<tspan fill="{GREEN}">  {status}</tspan>' if status else "")
            + "</text></g>"
        )
    term += (
        f'<rect x="20" y="{80 + 4*32 - 15}" width="9" height="17" fill="{INK}">'
        f'<animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect></g>'
    )
    text = (
        f'<text x="64" y="104" font-family="{MONO}" font-size="14" letter-spacing="3.5" fill="{VIOLET if light else "#C4B5FD"}">YUVIKA-OS · COMMAND CENTER</text>'
        f'<text x="62" y="168" font-size="60" font-weight="800" letter-spacing="-1.5" fill="{ink}">{e(NAME)}</text>'
        f'<text x="64" y="206" font-family="{MONO}" font-size="19" fill="{VIOLET if light else "#A78BFA"}">{e(ROLE)}</text>'
        f'<text x="64" y="240" font-size="18" fill="{dim}">{e(TAGLINE)}</text>'
        f'<text x="64" y="270" font-family="{MONO}" font-size="14" fill="{dim}">◉ {e(LOCATION)}  ·  {e(EMAIL)}</text>'
    )
    hud = (
        f'<text x="{W-32}" y="{H-18}" text-anchor="end" font-family="{MONO}" font-size="12" letter-spacing="3" fill="{dim}">DREAM &gt; BUILD &gt; LEARN &gt; REPEAT</text>'
        f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="24" fill="none" stroke="url(#vb)" stroke-width="1.2"/>'
    )
    defs += f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="24"/></clipPath>'
    alt = f"{NAME} — {ROLE}. A night landscape with a crescent moon and a terminal booting her command center."
    return svg(W, H, f'<g clip-path="url(#frame)">{scene}{text}{term}{hud}</g>', defs, alt)


def launch() -> str:
    W, H = 560, 92
    defs = (
        '<filter id="glow" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="9"/></filter>'
        '<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".5" stop-color="#fff" stop-opacity=".22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<clipPath id="pill"><rect x="14" y="14" width="{W-28}" height="{H-28}" rx="{(H-28)/2}"/></clipPath>'
    )
    body = (
        f'<rect x="20" y="20" width="{W-40}" height="{H-40}" rx="{(H-40)/2}" fill="url(#vp)" filter="url(#glow)" opacity=".55">'
        f'<animate attributeName="opacity" values=".35;.75;.35" dur="2.6s" repeatCount="indefinite"/></rect>'
        f'<rect x="14" y="14" width="{W-28}" height="{H-28}" rx="{(H-28)/2}" fill="{NAVY}"/>'
        f'<g clip-path="url(#pill)"><rect x="-200" y="0" width="160" height="{H}" fill="url(#shine)">'
        f'<animateTransform attributeName="transform" type="translate" values="0 0;{W+240} 0" dur="3.2s" repeatCount="indefinite"/></rect></g>'
        f'<rect x="14.5" y="14.5" width="{W-29}" height="{H-29}" rx="{(H-29)/2}" fill="none" stroke="url(#vp)" stroke-width="1.6"/>'
        f'<text x="{W/2}" y="{H/2 + 7}" text-anchor="middle" font-family="{MONO}" font-size="19" font-weight="700" letter-spacing="3.5" fill="{INK}">▶  LAUNCH COMMAND CENTER</text>'
    )
    return svg(W, H, body, defs, "Launch Yuvika's interactive Command Center")


def card_profile(avatar_b64: str | None, H: int = 330) -> str:
    W = 600
    defs = (
        '<clipPath id="av"><circle cx="96" cy="104" r="54"/></clipPath>'
        f'<linearGradient id="ring" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{VIOLET}"/><stop offset=".5" stop-color="{CYAN}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
    )
    avatar = (
        f'<image x="42" y="50" width="108" height="108" clip-path="url(#av)" preserveAspectRatio="xMidYMid slice" href="data:image/jpeg;base64,{avatar_b64}"/>'
        if avatar_b64
        else f'<circle cx="96" cy="104" r="54" fill="#312E81"/>'
    )
    body = panel(W, H) + label(32, 34, "IDENTITY // ID-0X2027") + label(W - 32, 34, "31.2554° N", size=11, anchor="end")
    body += (
        f'<circle cx="96" cy="104" r="60" fill="none" stroke="url(#ring)" stroke-width="3" stroke-dasharray="300 80">'
        f'<animateTransform attributeName="transform" type="rotate" values="0 96 104;360 96 104" dur="8s" repeatCount="indefinite"/></circle>'
        f"{avatar}"
        f'<circle cx="138" cy="146" r="9" fill="{GREEN}" stroke="{NAVY}" stroke-width="3"><animate attributeName="opacity" values="1;.55;1" dur="2s" repeatCount="indefinite"/></circle>'
        f'<text x="180" y="96" font-size="30" font-weight="700" fill="{INK}">{e(NAME)}</text>'
        f'<text x="181" y="126" font-family="{MONO}" font-size="15" fill="#A78BFA">{e(ROLE)}</text>'
        f'<text x="181" y="154" font-size="15" fill="{DIM}">◉ {e(LOCATION)}</text>'
    )
    for i, ln in enumerate(wrap(BIO, 62, 2)):
        body += f'<text x="32" y="{198 + i*24}" font-size="16" fill="{INK}" fill-opacity=".9">{e(ln)}</text>'
    x = 32
    for f in FOCUS:
        c, w = chip(x, 238, f, VIOLET, 13)
        body += c
        x += w + 8
    # Contact block pinned to the bottom so the card can stretch to match the stack card.
    links = [("linkedin", LINKEDIN), ("email", EMAIL), ("site", SITE.replace("https://", ""))]
    for i, (k, v) in enumerate(links):
        y = 290 + i * 22
        body += f'<text x="32" y="{y}" font-family="{MONO}" font-size="13" fill="{DIM}">{k:<9}</text><text x="112" y="{y}" font-family="{MONO}" font-size="13" fill="{INK}">{e(v)}</text>'
    b = H - 22
    body += (
        f'<line x1="32" x2="{W-32}" y1="{b-26}" y2="{b-26}" stroke="#fff" stroke-opacity=".08"/>'
        f'<circle cx="40" cy="{b-5}" r="5" fill="{GREEN}"/><text x="54" y="{b}" font-family="{MONO}" font-size="13" fill="{GREEN}">open to AI/ML roles</text>'
        f'<text x="{W-32}" y="{b}" text-anchor="end" font-family="{MONO}" font-size="13" fill="{CYAN}">connect on LinkedIn ↗</text>'
    )
    return svg(W, H, body, defs, f"{NAME}, {ROLE}, {LOCATION}. Focus: {', '.join(FOCUS)}. Connect on LinkedIn.")


def card_stack() -> tuple[int, str]:
    W = 600
    body, y = "", 70
    for group, items in SKILLS:
        body += label(32, y, group, size=12)
        y += 12
        x = 32
        for name, color in items:
            c, w = chip(x, y, name, color, 13)
            if x + w > W - 32:
                x, y = 32, y + 36
                c, w = chip(x, y, name, color, 13)
            body += c
            x += w + 8
        y += 54
    H = y - 10
    head = panel(W, H) + label(32, 38, "TECH STACK", INK, 14) + label(W - 32, 38, "explore ↗", CYAN, 13, "end")
    return H, svg(W, H, head + body, "", "Tech stack: " + "; ".join(f"{g.title()}: {', '.join(n for n, _ in items)}" for g, items in SKILLS))


def footer() -> str:
    W, H = 1200, 70
    body = (
        f'<line x1="40" x2="{W-40}" y1="18" y2="18" stroke="url(#vp)" stroke-opacity=".5"/>'
        f'<text x="{W/2}" y="52" text-anchor="middle" font-family="{MONO}" font-size="15" letter-spacing="5" fill="#A78BFA">'
        f'DREAM <tspan fill="{PINK}">&gt;</tspan> BUILD <tspan fill="{PINK}">&gt;</tspan> LEARN <tspan fill="{PINK}">&gt;</tspan> REPEAT</text>'
    )
    return svg(W, H, body, "", "Dream, build, learn, repeat.")


# ── live data ───────────────────────────────────────────────────────────────────────────────────────────────────
QUERY = """
query($login:String!){ user(login:$login){
  pinnedItems(first:6, types:REPOSITORY){ nodes{ ... on Repository{ name } } }
  repositories(first:100, privacy:PUBLIC, ownerAffiliations:OWNER, orderBy:{field:PUSHED_AT, direction:DESC}){
    totalCount
    nodes{ name description url homepageUrl isFork isArchived isEmpty stargazerCount pushedAt
      primaryLanguage{ name color }
      repositoryTopics(first:20){ nodes{ topic{ name } } }
      defaultBranchRef{ target{ ... on Commit{ history(first:1){ nodes{ messageHeadline committedDate } } } } }
      portfolio: object(expression:"HEAD:.portfolio.json"){ ... on Blob{ text } } } }
  contributionsCollection{ contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } } }
} }
"""


def gql(token: str, login: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "command-center-readme"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if body.get("errors") or not body.get("data"):
        raise SystemExit(f"GraphQL error: {body.get('errors')}")
    return body["data"]["user"]


def ago(iso: str) -> str:
    s = int((dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds())
    for n, u in ((31536000, "y"), (2592000, "mo"), (604800, "w"), (86400, "d"), (3600, "h"), (60, "m")):
        if s >= n:
            return f"{s // n}{u} ago"
    return "just now"


def collect(user: dict, login: str) -> dict:
    pinned = [n["name"] for n in user["pinnedItems"]["nodes"] if n.get("name")]
    repos = []
    for n in user["repositories"]["nodes"]:
        topics = [t["topic"]["name"] for t in n["repositoryTopics"]["nodes"]]
        if n["isFork"] or n["isArchived"] or n["isEmpty"] or n["name"].lower() == login.lower() or HIDE_TOPIC in topics:
            continue
        progress = None
        try:
            p = json.loads((n.get("portfolio") or {}).get("text") or "null") or {}
            if isinstance(p.get("progress"), (int, float)):
                progress = max(0, min(100, round(p["progress"])))
            tagline = p.get("tagline") if isinstance(p.get("tagline"), str) else None
        except (ValueError, AttributeError):
            tagline = None
        head = (((n.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {}).get("nodes") or []
        repos.append({
            "name": n["name"], "description": tagline or n["description"] or "", "url": n["url"], "homepage": n["homepageUrl"] or "",
            "stars": n["stargazerCount"], "pushedAt": n["pushedAt"], "topics": topics,
            "language": (n["primaryLanguage"] or {}).get("name"), "color": (n["primaryLanguage"] or {}).get("color") or VIOLET,
            "lastCommit": head[0]["messageHeadline"] if head else "", "progress": progress,
        })
    rank = {name: i for i, name in enumerate(pinned)}
    repos.sort(key=lambda r: (rank.get(r["name"], 99), -dt.datetime.fromisoformat(r["pushedAt"].replace("Z", "+00:00")).timestamp()))
    featured = next((r for r in repos if FEATURE_TOPICS & set(r["topics"])), None) or max(repos, key=lambda r: r["pushedAt"], default=None)

    days = sorted((d["date"], d["contributionCount"]) for w in user["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"])
    counts = dict(days)
    today = dt.datetime.now(dt.timezone.utc).date()
    d = today if counts.get(today.isoformat(), 0) else today - dt.timedelta(days=1)
    streak = 0
    while counts.get(d.isoformat(), 0) > 0:
        streak += 1
        d -= dt.timedelta(days=1)
    langs: dict[str, int] = {}
    for r in repos:
        if r["language"]:
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    last = max(repos, key=lambda r: r["pushedAt"], default=None)
    return {
        "repos": repos, "featured": featured, "pinned": pinned,
        "stats": {
            "week": sum(c for _, c in days[-7:]), "streak": streak, "year": user["contributionsCollection"]["contributionCalendar"]["totalContributions"],
            "top": max(langs, key=langs.get) if langs else "—", "last": last, "stars": sum(r["stars"] for r in repos), "shown": len(repos),
        },
    }


def status_svg(st: dict, stamp: str) -> str:
    W, H = 1200, 230
    body = panel(W, H) + label(36, 42, "SYSTEM STATUS", INK, 14)
    body += (
        f'<circle cx="{W-150}" cy="37" r="6" fill="{GREEN}"><animate attributeName="opacity" values="1;.35;1" dur="1.6s" repeatCount="indefinite"/></circle>'
        + label(W - 36, 42, "LIVE · GITHUB API", GREEN, 12, "end")
    )
    last = st["last"]
    tiles = [
        ("CONTRIBUTIONS · 7 DAYS", str(st["week"]), f'{st["year"]} this year', VIOLET),
        ("CURRENT STREAK", f'{st["streak"]}d', "days in a row", PINK),
        ("TOP LANGUAGE", st["top"], f'across {st["shown"]} repos', BLUE),
        ("LAST PUSHED", clip(last["name"], 17) if last else "—", ago(last["pushedAt"]) if last else "", CYAN),
    ]
    for i, (lab, val, sub, col) in enumerate(tiles):
        x = 36 + i * 284
        size = 40 if len(val) <= 9 else 26
        body += (
            f'<g transform="translate({x} 64)"><rect width="266" height="120" rx="14" fill="{col}" fill-opacity=".07" stroke="{col}" stroke-opacity=".4"/>'
            f'<text x="20" y="32" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{col}">{e(lab)}</text>'
            f'<text x="20" y="{78 if size == 40 else 74}" font-size="{size}" font-weight="800" fill="{INK}">{e(val)}'
            f'<animate attributeName="opacity" values="0;1" dur=".8s" begin="{i*0.15}s" fill="freeze"/></text>'
            f'<text x="20" y="104" font-family="{MONO}" font-size="13" fill="{DIM}">{e(sub)}</text></g>'
        )
    body += f'<text x="{W-36}" y="{H-18}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{DIM}" fill-opacity=".8">updated {e(stamp)}</text>'
    alt = f'System status: {st["week"]} contributions in the last 7 days, {st["streak"]}-day streak, top language {st["top"]}' + (f', last pushed {last["name"]} {ago(last["pushedAt"])}.' if last else ".")
    return svg(W, H, body, "", alt)


def tech_of(r: dict, limit: int) -> list[tuple[str, str]]:
    out, seen = [], set()
    for key, col in [(r["language"], r["color"])] + [TECH.get(t, (t, VIOLET)) for t in r["topics"] if t not in FEATURE_TOPICS]:
        if key and key.lower() not in seen:
            seen.add(key.lower())
            out.append((key, col))
    return out[:limit]


def now_building_svg(r: dict) -> str:
    W, H = 1200, 300
    defs = (
        f'<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>'
        f'<stop offset=".85" stop-color="{CYAN}" stop-opacity=".35"/><stop offset="1" stop-color="#A5F3FC"/></linearGradient>'
        '<clipPath id="doc"><rect x="820" y="54" width="340" height="206" rx="12"/></clipPath>'
    )
    body = panel(W, H)
    body += (
        f'<circle cx="44" cy="38" r="6" fill="{GREEN}"><animate attributeName="opacity" values="1;.35;1" dur="1.6s" repeatCount="indefinite"/></circle>'
        + label(60, 43, "NOW BUILDING", INK, 14)
        + f'<text x="36" y="104" font-size="40" font-weight="800" letter-spacing="-.5" fill="{INK}">{e(clip(r["name"].replace("-", " ").replace("_", " "), 34))}</text>'
    )
    for i, ln in enumerate(wrap(r["description"] or "No description yet.", 68, 2)):
        body += f'<text x="36" y="{142 + i*26}" font-size="19" fill="{INK}" fill-opacity=".85">{e(ln)}</text>'
    x = 36
    for name, col in tech_of(r, 5):
        c, w = chip(x, 192, name, col, 14)
        if x + w > 780:
            break
        body += c
        x += w + 8
    if r["progress"] is not None:
        p = r["progress"]
        body += (
            f'<text x="36" y="254" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{DIM}">BUILD PROGRESS · {p}%</text>'
            f'<rect x="36" y="264" width="440" height="8" rx="4" fill="#fff" fill-opacity=".08"/>'
            f'<rect x="36" y="264" width="{440*p/100:.0f}" height="8" rx="4" fill="url(#vp)"><animate attributeName="width" values="0;{440*p/100:.0f}" dur="1.4s" fill="freeze"/></rect>'
        )
    elif r["lastCommit"]:
        body += f'<text x="36" y="262" font-family="{MONO}" font-size="14" fill="{DIM}"><tspan fill="{GREEN}">last commit {e(ago(r["pushedAt"]))}</tspan> — {e(clip(r["lastCommit"], 56))}</text>'
    # Simplified scan visual: a code panel being swept by a scan line.
    body += f'<rect x="820" y="54" width="340" height="206" rx="12" fill="{BASE}" stroke="url(#vb)"/>'
    rnd = random.Random(r["name"])
    for i in range(9):
        y = 82 + i * 20
        indent = rnd.choice([0, 0, 18, 36])
        wdt = rnd.randint(90, 250 - indent)
        col = rnd.choice([VIOLET, CYAN, PINK, DIM, DIM])
        body += f'<rect x="{842 + indent}" y="{y}" width="{wdt}" height="6" rx="3" fill="{col}" fill-opacity=".55"/>'
    body += (
        f'<rect x="836" y="{82 + 4*20 - 7}" width="290" height="20" rx="4" fill="none" stroke="{PINK}" stroke-width="1.2" opacity="0">'
        f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;.4;.48;.9;1" dur="6s" repeatCount="indefinite"/></rect>'
        f'<g clip-path="url(#doc)"><rect x="820" y="20" width="340" height="34" fill="url(#beam)">'
        f'<animateTransform attributeName="transform" type="translate" values="0 0;0 240;0 240" keyTimes="0;.45;1" dur="6s" repeatCount="indefinite"/></rect></g>'
        f'<text x="990" y="284" text-anchor="middle" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{DIM}">pushed {e(ago(r["pushedAt"]))}</text>'
    )
    return svg(W, H, body, defs, f'Now building: {r["name"]} — {r["description"]}')


def projects_svg(repos: list[dict], featured: str | None, pinned: list[str]) -> str:
    top = repos[:4]
    W = 1200
    rows = max(1, math.ceil(len(top) / 2))
    H = 74 + rows * 176
    body = panel(W, H) + label(36, 42, "PROJECTS · LIVE FROM GITHUB", INK, 14) + label(W - 36, 42, f"{len(repos)} repositories", DIM, 12, "end")
    for i, r in enumerate(top):
        x, y = 36 + (i % 2) * 570, 66 + (i // 2) * 176
        tag = "NOW BUILDING" if r["name"] == featured else ("PINNED" if r["name"] in pinned else "")
        body += f'<g transform="translate({x} {y})"><rect width="558" height="160" rx="14" fill="#fff" fill-opacity=".03" stroke="#fff" stroke-opacity=".09"/>'
        body += f'<text x="22" y="40" font-size="22" font-weight="700" fill="{INK}">{e(clip(r["name"].replace("-", " ").replace("_", " "), 34 if not tag else 28))}</text>'
        if tag:
            body += f'<text x="536" y="38" text-anchor="end" font-family="{MONO}" font-size="11" letter-spacing="1.5" fill="{PINK}">{tag}</text>'
        for j, ln in enumerate(wrap(r["description"] or "No description yet.", 58, 2)):
            body += f'<text x="22" y="{74 + j*23}" font-size="16" fill="{DIM}">{e(ln)}</text>'
        body += (
            f'<circle cx="28" cy="135" r="6" fill="{r["color"]}"/><text x="42" y="140" font-family="{MONO}" font-size="14" fill="{INK}">{e(r["language"] or "—")}</text>'
            f'<text x="536" y="140" text-anchor="end" font-family="{MONO}" font-size="14" fill="{DIM}">★ {r["stars"]}  ·  {e(ago(r["pushedAt"]))}</text></g>'
        )
    return svg(W, H, body, "", "Top projects: " + "; ".join(f'{r["name"]} ({r["language"] or "n/a"}, {r["stars"]} stars)' for r in top))


def replace_block(text: str, tag: str, content: str) -> str:
    pattern = re.compile(rf"(<!-- {tag}:START -->)(.*?)(<!-- {tag}:END -->)", re.S)
    return pattern.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text)


def update_readme(path: pathlib.Path, data: dict, login: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text()
    if "<!-- PROJECTS:START -->" not in text and "<!-- NOW:START -->" not in text:
        return False  # current README has no markers: leave it untouched
    rows = [f'| [**{r["name"]}**]({r["url"]}) | {e(r["description"] or "—")} | {r["language"] or "—"} | ★ {r["stars"]} |' for r in data["repos"]]
    projects = "| Project | What it is | Language | Stars |\n|:--|:--|:--|--:|\n" + "\n".join(rows)
    f = data["featured"]
    raw = f"https://raw.githubusercontent.com/{login}/{login}/output"
    now = (
        f'<a href="{f["url"]}"><img src="{raw}/cc-now-building.svg" width="100%" alt="Now building: {e(f["name"])} — {e(f["description"])}" /></a>'
        if f
        else ""
    )
    new = replace_block(replace_block(text, "PROJECTS", projects), "NOW", now)
    if new != text:
        path.write_text(new)
        return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["static", "live"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "Yuvika687"))
    ap.add_argument("--readme")
    ap.add_argument("--avatar", help="JPEG for the profile card (embedded as base64)")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    if a.mode == "static":
        av = base64.b64encode(pathlib.Path(a.avatar).read_bytes()).decode() if a.avatar else None
        stack_h, stack = card_stack()
        files = {"hero-dark.svg": hero(False), "hero-light.svg": hero(True), "launch.svg": launch(),
                 "card-profile.svg": card_profile(av, max(400, stack_h)), "card-stack.svg": stack, "footer.svg": footer()}
    else:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            sys.exit("GITHUB_TOKEN is required")
        data = collect(gql(token, a.user), a.user)
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        files = {"cc-status.svg": status_svg(data["stats"], stamp), "cc-projects.svg": projects_svg(data["repos"], (data["featured"] or {}).get("name"), data["pinned"])}
        if data["featured"]:
            files["cc-now-building.svg"] = now_building_svg(data["featured"])
        if a.readme and update_readme(pathlib.Path(a.readme), data, a.user):
            print("README project links updated")
    for name, content in files.items():
        (out / name).write_text(content)
        print(f"wrote {out / name} ({len(content) // 1024} KB)")


if __name__ == "__main__":
    main()
