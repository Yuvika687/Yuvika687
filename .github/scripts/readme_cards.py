#!/usr/bin/env python3
"""Profile README cards — one painted night scene, gently animated.

  static  hero, about, focus, tech stack, footer  → assets/*.svg (committed; rebuilt when readme-config.json changes)
            python3 .github/scripts/readme_cards.py static --out assets
  live    now building, GitHub stats, projects    → dist/*.svg (published to the `output` branch every 6h)
          + the "Every project" list / Now Building link between the README markers
            GITHUB_TOKEN=... python3 .github/scripts/readme_cards.py live --user Yuvika687 --out dist --readme README.md

Standard library only. Text and copy live in readme-config.json; art, fonts and icons in .github/readme/.
GitHub renders README SVGs as <img>: no external fetches (so images/fonts are embedded as base64), no hover,
and only CSS/SMIL animation. Everything here is CSS so `prefers-reduced-motion` can stop all of it, and every
element's resting style is its final frame — with motion off the cards simply appear finished.
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
import zlib
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parents[2]
ART = ROOT / ".github" / "readme"
CONFIG = json.loads((ROOT / "readme-config.json").read_text())

VIOLET, PURPLE, BLUE, PINK, GREEN, CYAN = "#8B5CF6", "#A855F7", "#3B82F6", "#EC4899", "#22C55E", "#22D3EE"
INK, DIM, LAV = "#E5E7FF", "#A9AED6", "#C4B5FD"
SANS = "I,-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "M,ui-monospace,'SF Mono',Menlo,Consolas,monospace"
MONO_W = 0.6  # JetBrains Mono advance width (em): lets the typing cursor track the text exactly
PAD = 14      # transparent margin around cards for the soft outer shadow (light theme)
FEATURE_TOPICS = {"featured", "now-building"}
HIDE_TOPIC = "hide-from-portfolio"

# Repo topic → (label, colour) for chips; unknown topics fall back to the raw topic.
TECH = {
    "python": ("Python", "#3776AB"), "javascript": ("JavaScript", "#F7DF1E"), "typescript": ("TypeScript", "#3178C6"), "cpp": ("C++", "#00599C"),
    "html": ("HTML", "#E34F26"), "css": ("CSS", "#663399"), "jupyter-notebook": ("Jupyter", "#F37626"), "pytorch": ("PyTorch", "#EE4C2C"),
    "opencv": ("OpenCV", "#5C3EE8"), "scikit-learn": ("scikit-learn", "#F7931E"), "xgboost": ("XGBoost", "#189FDD"), "lightgbm": ("LightGBM", "#9ACD32"),
    "catboost": ("CatBoost", "#FFCC00"), "huggingface": ("Hugging Face", "#FFD21E"), "fastapi": ("FastAPI", "#009688"), "streamlit": ("Streamlit", "#FF4B4B"),
    "nextjs": ("Next.js", INK), "postgresql": ("PostgreSQL", "#4169E1"), "docker": ("Docker", "#2496ED"), "jwt": ("JWT", INK), "mediapipe": ("MediaPipe", "#0097A7"),
    "gemini": ("Gemini", "#8E75B2"), "pandas": ("Pandas", "#E70488"), "llm": ("LLM", PINK), "computer-vision": ("Computer Vision", PURPLE),
    "machine-learning": ("Machine Learning", VIOLET), "full-stack": ("Full-stack", BLUE), "chrome-extension": ("Chrome Extension", "#4285F4"),
    "spaced-repetition": ("Spaced Repetition", CYAN), "unsupervised-learning": ("Unsupervised Learning", VIOLET), "pose-estimation": ("Pose Estimation", CYAN),
    "bot-detection": ("Bot Detection", PINK), "crowd-counting": ("Crowd Counting", PURPLE), "ai-gateway": ("AI Gateway", PINK),
}

# Tech-stack label → (Simple Icons slug or None for a monogram, brand colour)
ICON = {
    "Python": ("python", "#3776AB"), "C++": ("cplusplus", "#00599C"), "C": ("c", "#A8B9CC"), "SQL": (None, "#22D3EE"),
    "JavaScript": ("javascript", "#F7DF1E"), "HTML": ("html5", "#E34F26"), "CSS": ("css", "#663399"), "PyTorch": ("pytorch", "#EE4C2C"),
    "OpenCV": ("opencv", "#5C3EE8"), "Scikit-learn": ("scikitlearn", "#F7931E"), "XGBoost": (None, "#189FDD"), "LightGBM": (None, "#9ACD32"),
    "CatBoost": (None, "#FFCC00"), "Hugging Face": ("huggingface", "#FFD21E"), "NumPy": ("numpy", "#4DABCF"), "Pandas": ("pandas", "#E70488"),
    "FastAPI": ("fastapi", "#009688"), "Flask": ("flask", INK), "Streamlit": ("streamlit", "#FF4B4B"), "SQLAlchemy": ("sqlalchemy", "#D71F00"),
    "JWT": ("jsonwebtokens", INK), "PostgreSQL": ("postgresql", "#4169E1"), "MySQL": ("mysql", "#4479A1"), "SQLite": ("sqlite", "#4FA3D8"),
    "Git": ("git", "#F05032"), "GitHub": ("github", INK), "Linux": ("linux", "#FCC624"),
}
MONOGRAM = {"SQL": "SQL", "XGBoost": "XGB", "LightGBM": "LGBM", "CatBoost": "CB"}


def e(s) -> str:
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
    if " ".join(out) != " ".join(words):
        out[-1] = clip(out[-1] + " …", width)
    return out


def b64(path: pathlib.Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


_FONT_CACHE: dict[str, str] = {}


def fonts(*names: str) -> str:
    """@font-face rules for the embedded subsets actually used by a card (I = Inter, M = JetBrains Mono)."""
    rules = []
    for n in names:
        if n not in _FONT_CACHE:
            _FONT_CACHE[n] = b64(ART / "fonts" / f"{n}.woff2")
        fam, weight = ("I", n.split("-")[1]) if n.startswith("inter") else ("M", n.split("-")[1])
        rules.append(f"@font-face{{font-family:{fam};font-weight:{weight};src:url(data:font/woff2;base64,{_FONT_CACHE[n]}) format('woff2')}}")
    return "".join(rules)


BASE_CSS = (
    ".s{font-family:%s}.m{font-family:%s}"
    "@keyframes rise{from{opacity:0;transform:translateY(12px)}}"
    "@keyframes fade{from{opacity:0}}"
    "@keyframes pulse{50%%{opacity:.35}}"
    "@keyframes blink{50%%{opacity:0}}"
    ".rise{animation:rise .9s cubic-bezier(.2,.8,.2,1) backwards}"
    ".fade{animation:fade 1s ease-out backwards}"
    ".pulse{animation:pulse 2.4s ease-in-out infinite}"
    ".blink{animation:blink 1.1s steps(1) infinite}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
) % (SANS, MONO)


def svg(w: int, h: int, body: str, css: str = "", defs: str = "", title: str = "") -> str:
    t = f"<title>{e(title)}</title>" if title else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">'
        f"{t}<style>{css}{BASE_CSS}</style><defs>"
        f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{VIOLET}" stop-opacity=".75"/>'
        f'<stop offset=".55" stop-color="{BLUE}" stop-opacity=".3"/><stop offset="1" stop-color="{VIOLET}" stop-opacity=".18"/></linearGradient>'
        f'<linearGradient id="vp" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
        f'<filter id="shadow" x="-8%" y="-10%" width="116%" height="130%"><feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#1E1B4B" flood-opacity=".32"/></filter>'
        f"{defs}</defs>{body}</svg>"
    )


BG = CONFIG.get("background", {})
# Overrides used only when previewing alternatives (e.g. picking a blur strength).
BG_DIR = pathlib.Path(os.environ.get("README_BG_DIR", ART / "bg"))
OVERLAY = float(os.environ.get("README_BG_OVERLAY", BG.get("overlay", 0.6)))


def card(w: int, h: int, inner: str, bg: str, text: str = "left") -> tuple[int, int, str]:
    """A card on its own softly blurred crop of the painting ("frosted glass").

    `bg` names the crop in .github/readme/bg/. A medium dark overlay keeps the scene recognisable but quiet, and
    `text` adds a darker gradient where the text sits: "left" (text column on the left) or "all" (text everywhere).
    """
    img = b64(BG_DIR / f"{bg}.jpg")
    shade = (
        '<linearGradient id="textshade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#05060F" stop-opacity=".5"/>'
        '<stop offset=".45" stop-color="#05060F" stop-opacity=".28"/><stop offset=".78" stop-color="#05060F" stop-opacity="0"/></linearGradient>'
        if text == "left"
        else '<linearGradient id="textshade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#05060F" stop-opacity=".18"/>'
        '<stop offset="1" stop-color="#05060F" stop-opacity=".32"/></linearGradient>'
    )
    body = (
        f"<defs>{shade}</defs>"
        f'<g transform="translate({PAD} {PAD})">'
        f'<rect width="{w}" height="{h}" rx="16" fill="#0B0D1F" filter="url(#shadow)"/>'
        f'<clipPath id="cardclip"><rect width="{w}" height="{h}" rx="16"/></clipPath>'
        f'<g clip-path="url(#cardclip)">'
        f'<image width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice" href="data:image/jpeg;base64,{img}"/>'
        f'<rect width="{w}" height="{h}" fill="#05060F" opacity="{OVERLAY:.2f}"/>'
        f'<rect width="{w}" height="{h}" fill="url(#textshade)"/>'
        f'<line x1="{w*.12:.0f}" x2="{w*.88:.0f}" y1="1" y2="1" stroke="#fff" stroke-opacity=".14"/>'
        f"{inner}</g>"
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="16" fill="none" stroke="url(#edge)"/></g>'
    )
    return w + 2 * PAD, h + 2 * PAD, body


def sky_life(w: int, region: tuple[float, float, float, float], seed: int, shoot_delay: float) -> tuple[str, str]:
    """A few slow twinkling stars and one rare, slow shooting star (every 16s) inside `region` (x0, y0, x1, y1)."""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = region
    stars = "".join(
        f'<circle cx="{rnd.uniform(x0, x1):.0f}" cy="{rnd.uniform(y0, y1):.0f}" r="{rnd.choice([0.8, 1, 1.2]):.1f}" fill="#fff" class="tw" '
        f'style="animation-duration:{rnd.uniform(4.5, 8):.1f}s;animation-delay:{-rnd.uniform(0, 8):.1f}s"/>'
        for _ in range(7)
    )
    sx, sy = rnd.uniform(x0 + (x1 - x0) * 0.45, x1 - 20), rnd.uniform(y0, y0 + (y1 - y0) * 0.4)
    css = (
        "@keyframes tw{50%{opacity:.12}}.tw{animation:tw ease-in-out infinite}"
        "@keyframes slowshoot{0%{opacity:0;transform:translate(0,0)}1.5%{opacity:.85}7%{opacity:0;transform:translate(-170px,62px)}100%{opacity:0;transform:translate(-170px,62px)}}"
        f".sshoot{{opacity:0;animation:slowshoot 16s linear {shoot_delay:.1f}s infinite}}"
    )
    shoot = (
        f'<g class="sshoot"><line x1="{sx:.0f}" y1="{sy:.0f}" x2="{sx + 70:.0f}" y2="{sy - 26:.0f}" stroke="url(#stail)" stroke-width="1.3" stroke-linecap="round"/>'
        f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="1.3" fill="#fff"/></g>'
    )
    defs = '<defs><linearGradient id="stail" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>'
    return defs + stars + shoot, css


def label(x: float, y: float, text: str, color: str = DIM, size: int = 12, anchor: str = "start", extra: str = "") -> str:
    return f'<text x="{x}" y="{y}" class="m" font-size="{size}" letter-spacing="3" fill="{color}" text-anchor="{anchor}" {extra}>{e(text)}</text>'


def live_dot(x: float, y: float, r: float = 5) -> str:
    return f'<circle cx="{x}" cy="{y}" r="{r*2.2:.1f}" fill="{GREEN}" opacity=".18" class="pulse"/><circle cx="{x}" cy="{y}" r="{r}" fill="{GREEN}"/>'


def chip(x: float, y: float, text: str, color: str, size: int = 14) -> tuple[str, float]:
    w = len(text) * size * 0.56 + 32
    h = size + 14
    return (
        f'<g transform="translate({x:.0f} {y:.0f})"><rect width="{w:.0f}" height="{h}" rx="8" fill="{color}" fill-opacity=".12" stroke="{color}" stroke-opacity=".5"/>'
        f'<circle cx="13" cy="{h/2:.1f}" r="3.6" fill="{color}"/><text x="24" y="{h/2 + size*0.36:.1f}" class="s" font-size="{size}" fill="{INK}">{e(text)}</text></g>',
        w,
    )


def typed(x: float, y: float, text: str, size: int, color: str, start: float, cps: float = 26, cursor: bool = False, extra_cls: str = "") -> tuple[str, str, float]:
    """One-shot typing reveal (clip grows in character steps). Returns (svg, css, end_time)."""
    n = len(text)
    width = n * size * MONO_W
    dur = n / cps
    uid = f"ty{zlib.crc32(f'{x}|{y}|{text}'.encode()):08x}"  # stable across runs (no spurious diffs)
    css = (
        f"@keyframes {uid}{{from{{transform:scaleX(0)}}}}"
        f".{uid}{{transform-box:fill-box;transform-origin:0 0;animation:{uid} {dur:.2f}s steps({n},end) {start:.2f}s backwards}}"
    )
    out = (
        f'<clipPath id="{uid}c"><rect class="{uid}" x="{x-1}" y="{y-size}" width="{width+2:.1f}" height="{size*1.5:.0f}"/></clipPath>'
        f'<text x="{x}" y="{y}" class="m {extra_cls}" font-size="{size}" fill="{color}" clip-path="url(#{uid}c)" xml:space="preserve">{e(text)}</text>'
    )
    if cursor:
        out += f'<rect x="{x + width + 3:.1f}" y="{y - size*0.82:.1f}" width="{size*0.55:.1f}" height="{size*1.02:.1f}" fill="{INK}" class="blink fade" style="animation-delay:{start+dur:.2f}s,{start+dur:.2f}s"/>'
    return out, css, start + dur


# ── static: hero ────────────────────────────────────────────────────────────────────────────────────────────────
def hero() -> str:
    W, H = 1200, 400
    rnd = random.Random(42)
    MOON = (934, 146)
    css = fonts("inter-800", "inter-400", "mono-400", "mono-700")
    css += (
        "@keyframes tw{50%{opacity:.15}}.tw{animation:tw ease-in-out infinite}"
        "@keyframes moon{50%{opacity:.95;transform:scale(1.05)}}.moon{transform-box:fill-box;transform-origin:center;animation:moon 6s ease-in-out infinite}"
        "@keyframes shoot{0%{opacity:0;transform:translate(0,0)}2%{opacity:1}9%{opacity:0;transform:translate(-300px,120px)}100%{opacity:0;transform:translate(-300px,120px)}}"
        ".shoot{animation:shoot 10s linear 3s infinite;opacity:0}"
        "@keyframes shim{50%{opacity:.15;transform:translateX(5px)}}.shim{animation:shim ease-in-out infinite}"
        "@keyframes fly{33%{transform:translate(9px,-7px)}66%{transform:translate(-6px,-12px)}}@keyframes glow{50%{opacity:.25}}"
        ".fly{animation:fly ease-in-out infinite}.fly circle{animation:glow ease-in-out infinite}"
    )
    # Cycling typing line: 4 phrases, 4s each (type 1.4s, hold, erase 0.5s).
    phrases = CONFIG["typing"]
    TX, TY, TS = 92, 278, 19
    cyc = 4.0 * len(phrases)
    lines = ""
    for i, p in enumerate(phrases):
        n = len(p)
        a = i * 4.0 / cyc * 100
        t1, t2, t3 = (i * 4 + 1.4) / cyc * 100, (i * 4 + 3.3) / cyc * 100, (i * 4 + 3.8) / cyc * 100
        b = (i + 1) * 4.0 / cyc * 100
        width = n * TS * MONO_W
        vis_default = 1 if i == 0 else 0  # reduced motion: show the first phrase only
        css += (
            f"@keyframes c{i}{{0%{{transform:scaleX(0)}}{a:.2f}%{{transform:scaleX(0);animation-timing-function:steps({n},end)}}"
            f"{t1:.2f}%{{transform:scaleX(1)}}{t2:.2f}%{{transform:scaleX(1);animation-timing-function:steps({n},end)}}{t3:.2f}%{{transform:scaleX(0)}}100%{{transform:scaleX(0)}}}}"
            f".c{i}{{transform-box:fill-box;transform-origin:0 0;animation:c{i} {cyc:.0f}s linear infinite}}"
            f"@keyframes k{i}{{0%,{a:.2f}%{{opacity:0;transform:translateX(0)}}{a+0.01:.2f}%{{opacity:1;transform:translateX(0);animation-timing-function:steps({n},end)}}"
            f"{t1:.2f}%{{transform:translateX({width:.1f}px)}}{t2:.2f}%{{transform:translateX({width:.1f}px);animation-timing-function:steps({n},end)}}"
            f"{t3:.2f}%{{opacity:1;transform:translateX(0)}}{b-0.01:.2f}%{{opacity:1}}{b:.2f}%,100%{{opacity:0}}}}"
            f".k{i}{{animation:k{i} {cyc:.0f}s linear infinite}}"
        )
        lines += (
            f'<clipPath id="tc{i}"><rect class="c{i}" x="{TX-1}" y="{TY-TS}" width="{width+2:.1f}" height="{TS*1.5:.0f}"/></clipPath>'
            f'<text x="{TX}" y="{TY}" class="m" font-size="{TS}" fill="{INK}" clip-path="url(#tc{i})" opacity="{1}">{e(p)}</text>'
            f'<g class="k{i}" opacity="{vis_default}"><rect x="{TX + 3:.1f}" y="{TY - TS*0.82:.1f}" width="{TS*0.55:.1f}" height="{TS*1.02:.1f}" fill="{LAV}" class="blink"/></g>'
        )
        if i == 0:
            first_width = width
    # Reduced motion: a still frame — first phrase fully typed, cursor parked at its end, the others hidden.
    css += ("@media (prefers-reduced-motion:reduce){" + "".join(f".c{i}{{transform:scaleX(0)}}" for i in range(1, len(phrases)))
            + f".k0{{transform:translateX({first_width:.1f}px)}}}}")

    stars = ""
    for _ in range(22):
        while True:
            x, y = rnd.uniform(520, 1190), rnd.uniform(8, 175)
            if math.hypot(x - MOON[0], y - MOON[1]) > 150:
                break
        r = rnd.choice([0.8, 1.0, 1.2, 1.5])
        stars += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#fff" class="tw" style="animation-duration:{rnd.uniform(4,8):.1f}s;animation-delay:{-rnd.uniform(0,8):.1f}s"/>'
    for _ in range(6):  # a few in the dark left sky too
        x, y = rnd.uniform(40, 500), rnd.uniform(8, 60)
        stars += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="0.9" fill="#fff" class="tw" style="animation-duration:{rnd.uniform(5,9):.1f}s;animation-delay:{-rnd.uniform(0,8):.1f}s"/>'
    shimmer = ""
    for cx, spread in ((452, 26), (965, 34), (1120, 22)):
        for j in range(6):
            y = 322 + j * 9 + rnd.uniform(-2, 2)
            w = rnd.uniform(14, spread)
            shimmer += f'<rect x="{cx - w/2 + rnd.uniform(-8, 8):.0f}" y="{y:.0f}" width="{w:.0f}" height="1.3" rx=".6" fill="#E9D5FF" opacity=".55" class="shim" style="animation-duration:{rnd.uniform(4.5,7):.1f}s;animation-delay:{-rnd.uniform(0,6):.1f}s"/>'
    flies = ""
    for x, y in [(70, 300), (150, 262), (205, 318), (1080, 290), (1150, 255), (1172, 332)]:
        flies += (
            f'<g class="fly" style="animation-duration:{rnd.uniform(12,18):.1f}s;animation-delay:{-rnd.uniform(0,12):.1f}s">'
            f'<circle cx="{x}" cy="{y}" r="5" fill="#E9D5FF" opacity=".18" style="animation-duration:{rnd.uniform(3,5):.1f}s"/>'
            f'<circle cx="{x}" cy="{y}" r="1.6" fill="#F5F3FF" opacity=".9" style="animation-duration:{rnd.uniform(3,5):.1f}s"/></g>'
        )
    pin = '<path d="M0 -7a5 5 0 0 1 5 5c0 3.6-5 8-5 8s-5-4.4-5-8a5 5 0 0 1 5-5z" fill="none" stroke="#C4B5FD" stroke-width="1.6"/><circle r="1.8" cy="-2" fill="#C4B5FD"/>'
    defs = (
        '<linearGradient id="left" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#05060F" stop-opacity=".86"/>'
        '<stop offset=".34" stop-color="#05060F" stop-opacity=".6"/><stop offset=".6" stop-color="#05060F" stop-opacity="0"/></linearGradient>'
        '<radialGradient id="mg"><stop offset="0" stop-color="#F5D0FE" stop-opacity=".55"/><stop offset=".45" stop-color="#C084FC" stop-opacity=".18"/><stop offset="1" stop-color="#A855F7" stop-opacity="0"/></radialGradient>'
        '<linearGradient id="tail" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<filter id="nameglow" x="-5%" y="-30%" width="110%" height="160%"><feGaussianBlur stdDeviation="9"/></filter>'
        f'<clipPath id="hc"><rect width="{W}" height="{H}" rx="16"/></clipPath>'
    )
    name = e(CONFIG["name"])
    body = (
        f'<g transform="translate({PAD} {PAD})"><rect width="{W}" height="{H}" rx="16" fill="#0B0D1F" filter="url(#shadow)"/><g clip-path="url(#hc)">'
        f'<image width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice" href="data:image/jpeg;base64,{b64(ART / "hero.jpg")}"/>'
        f'<circle cx="{MOON[0]}" cy="{MOON[1]}" r="170" fill="url(#mg)" opacity=".7" class="moon" style="mix-blend-mode:screen"/>'
        f"{stars}"
        f'<g class="shoot"><line x1="880" y1="40" x2="980" y2="0" stroke="url(#tail)" stroke-width="1.6" stroke-linecap="round" transform="rotate(0)"/><circle cx="880" cy="40" r="1.6" fill="#fff"/></g>'
        f"{shimmer}{flies}"
        f'<rect width="{W}" height="{H}" fill="url(#left)"/>'
        f'<g class="rise" style="animation-delay:.15s">{label(64, 116, "HELLO WORLD, I’M", LAV, 13)}</g>'
        f'<g class="rise" style="animation-delay:.3s"><text x="60" y="190" class="s" font-size="66" font-weight="800" fill="{VIOLET}" opacity=".55" filter="url(#nameglow)">{name}</text>'
        f'<text x="60" y="190" class="s" font-size="66" font-weight="800" letter-spacing="-1.4" fill="#fff">{name}</text></g>'
        f'<g class="rise" style="animation-delay:.45s"><text x="64" y="232" class="m" font-size="20" fill="{LAV}">{e(CONFIG["role"])}</text></g>'
        f'<g class="fade" style="animation-delay:.7s"><text x="64" y="{TY}" class="m" font-size="{TS}" font-weight="700" fill="{PINK}">&gt;</text>{lines}</g>'
        f'<g class="rise" style="animation-delay:.6s"><g transform="translate(72 340)">{pin}</g>'
        f'<text x="86" y="345" class="s" font-size="16" fill="{INK}" opacity=".9">{e(CONFIG["location"])}  ·  </text>'
        f'{live_dot(238, 339, 4.5)}<text x="252" y="345" class="s" font-size="16" fill="{INK}" opacity=".9">{e(CONFIG["status"])}</text></g>'
        f'<text x="{W-34}" y="{H-24}" text-anchor="end" class="m" font-size="11.5" letter-spacing="3.5" fill="{INK}" opacity=".75">DREAM &gt; BUILD &gt; LEARN &gt; REPEAT</text>'
        f'</g><rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="16" fill="none" stroke="url(#edge)"/></g>'
    )
    alt = f'{CONFIG["name"]} — {CONFIG["role"]}. {CONFIG["location"]}, {CONFIG["status"]}. A painted night scene: mountains, a lake and a crescent moon.'
    return svg(W + 2 * PAD, H + 2 * PAD, body, css, defs, alt)


# ── static: about + focus (equal height, designed to sit side by side) ──────────────────────────────────────────
HALF_W, HALF_H = 600, 320


def about() -> str:
    css = fonts("mono-400", "mono-700")
    inner = (
        '<circle cx="26" cy="26" r="6" fill="#FF5F57"/><circle cx="46" cy="26" r="6" fill="#FEBC2E"/><circle cx="66" cy="26" r="6" fill="#28C840"/>'
        f'<text x="{HALF_W/2}" y="31" text-anchor="middle" class="m" font-size="13" fill="{DIM}">yuvika@dev: ~</text>'
        f'<line x1="0" x2="{HALF_W}" y1="50" y2="50" stroke="#fff" stroke-opacity=".08"/>'
    )
    y, t, size = 92, 0.5, 15
    for item in CONFIG["about"]:
        prompt = f'<text x="28" y="{y}" class="m" font-size="{size}" font-weight="700" fill="{GREEN}" style="animation-delay:{t:.2f}s" >$</text>'
        frag, c, t = typed(46, y, item["cmd"], size, INK, t, cps=18)
        inner += f'<g class="fade" style="animation-delay:{t - len(item["cmd"])/18:.2f}s">{prompt}</g>{frag}'
        css += c
        y += 30
        color = GREEN if item.get("tone") == "green" else LAV
        for ln in wrap(item["out"], 64, 2):  # 64 mono chars fit the 600px card
            inner += f'<g class="fade" style="animation-delay:{t + 0.25:.2f}s"><text x="28" y="{y}" class="m" font-size="{size - 1}" fill="{color}">{e(ln)}</text></g>'
            y += 24
        y += 14
        t += 0.55
    inner += (
        f'<g class="fade" style="animation-delay:{t:.2f}s"><text x="28" y="{y}" class="m" font-size="{size}" font-weight="700" fill="{GREEN}">$</text>'
        f'<rect x="46" y="{y - size*0.82:.1f}" width="{size*0.55:.1f}" height="{size*1.02:.1f}" fill="{INK}" class="blink"/></g>'
    )
    life, life_css = sky_life(HALF_W, (330, 60, 590, 150), seed=7, shoot_delay=5)
    w, h, body = card(HALF_W, HALF_H, life + inner, "about", text="all")
    return svg(w, h, body, css + life_css, "", "Terminal: whoami — " + "; ".join(i["out"] for i in CONFIG["about"]))


def focus() -> str:
    css = fonts("inter-700", "inter-400", "mono-400")
    css += "@keyframes tick{from{stroke-dashoffset:1}}.tick{stroke-dasharray:1;animation:tick .5s ease-out backwards}"
    f = CONFIG["focus"]
    inner = label(32, 44, "FOCUS", DIM, 12) + f'<text x="32" y="80" class="s" font-size="24" font-weight="700" fill="{INK}">{e(f["title"])}</text>'
    for i, it in enumerate(f["items"][:6]):
        y = 128 + i * 46
        d = 0.35 + i * 0.18
        box = (
            f'<rect x="32" y="{y-18}" width="24" height="24" rx="7" fill="url(#vp)" opacity=".95"/>'
            f'<path d="M38 {y-6} l5 5 l9 -10" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" pathLength="1" class="tick" style="animation-delay:{d + 0.35:.2f}s"/>'
            if it["done"]
            else f'<rect x="33" y="{y-17}" width="22" height="22" rx="6.5" fill="none" stroke="{LAV}" stroke-opacity=".7" stroke-width="1.6"/>'
        )
        inner += f'<g class="rise" style="animation-delay:{d:.2f}s">{box}<text x="72" y="{y}" class="s" font-size="18" fill="{INK}" opacity="{1 if it["done"] else .82}">{e(it["text"])}</text></g>'
    life, life_css = sky_life(HALF_W, (360, 14, 590, 140), seed=11, shoot_delay=11)
    css += life_css
    w, h, body = card(HALF_W, HALF_H, life + inner, "focus", text="left")
    alt = f["title"] + ": " + "; ".join(("done: " if it["done"] else "next: ") + it["text"] for it in f["items"])
    return svg(w, h, body, css, "", alt)


# ── static: tech stack ──────────────────────────────────────────────────────────────────────────────────────────
def luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def tech_stack() -> str:
    icons = json.loads((ART / "icons.json").read_text())
    css = fonts("inter-400", "mono-400", "mono-700")  # (no Inter bold here: keeps the card under 150 KB)
    css += "@keyframes pop{from{opacity:0;transform:scale(.6)}}.pop{transform-box:fill-box;transform-origin:center;animation:pop .5s cubic-bezier(.3,1.4,.5,1) backwards}"
    W, LEFT, PITCH, ROW = 1200, 200, 104, 96
    inner = label(36, 46, "TECH STACK", INK, 13)
    y, k = 82, 0
    for g in CONFIG["skills"]:
        inner += f'<g class="rise" style="animation-delay:{0.1 + k*0.02:.2f}s">{label(36, y + 30, g["group"].upper(), DIM, 11)}</g>'
        for j, name in enumerate(g["items"]):
            slug, color = ICON.get(name, (None, VIOLET))
            x = LEFT + j * PITCH
            fill = color if luminance(color) > 0.22 else INK
            if slug and slug in icons:
                glyph = f'<path d="{icons[slug]}" fill="{fill}" transform="translate({x + 31} {y + 9}) scale(1.75)"/>'
            else:
                mono = MONOGRAM.get(name, name[:3].upper())
                fs = 15 if len(mono) <= 3 else 12
                glyph = f'<text x="{x + 52}" y="{y + 34}" text-anchor="middle" class="m" font-size="{fs}" font-weight="700" fill="{fill}">{e(mono)}</text>'
            inner += (
                f'<g class="pop" style="animation-delay:{0.25 + k*0.045:.2f}s">'
                f'<rect x="{x + 26}" y="{y + 3}" width="52" height="54" rx="12" fill="{color}" fill-opacity=".1" stroke="{color}" stroke-opacity=".38"/>'
                f"{glyph}"
                f'<text x="{x + 52}" y="{y + 76}" text-anchor="middle" class="s" font-size="12.5" fill="{INK}" opacity=".88">{e(name)}</text></g>'
            )
            k += 1
        y += ROW
    H = y + 6
    w, h, body = card(W, H, inner, "tech-stack", text="left")
    return svg(w, h, body, css, "", "Tech stack — " + "; ".join(f'{g["group"]}: {", ".join(g["items"])}' for g in CONFIG["skills"]))


def footer() -> str:
    W, H = 1200, 64
    css = fonts("mono-400")
    body = (
        f'<line x1="60" x2="{W-60}" y1="14" y2="14" stroke="url(#vp)" stroke-opacity=".45"/>'
        f'<text x="{W/2}" y="48" text-anchor="middle" class="m" font-size="15" letter-spacing="6" fill="{VIOLET}">'
        f'DREAM <tspan fill="{PINK}">&gt;</tspan> BUILD <tspan fill="{PINK}">&gt;</tspan> LEARN <tspan fill="{PINK}">&gt;</tspan> REPEAT</text>'
    )
    return svg(W, H, body, css, "", "Dream, build, learn, repeat.")


# ── live data ───────────────────────────────────────────────────────────────────────────────────────────────────
QUERY = """
query($login:String!){ user(login:$login){
  pinnedItems(first:6, types:REPOSITORY){ nodes{ ... on Repository{ name } } }
  repositories(first:100, privacy:PUBLIC, ownerAffiliations:OWNER, orderBy:{field:PUSHED_AT, direction:DESC}){
    nodes{ name description url homepageUrl isFork isArchived isEmpty isPrivate stargazerCount pushedAt
      primaryLanguage{ name color }
      repositoryTopics(first:20){ nodes{ topic{ name } } }
      defaultBranchRef{ name target{ ... on Commit{ history(first:8){ nodes{ oid messageHeadline committedDate } } } } }
      portfolio: object(expression:"HEAD:.portfolio.json"){ ... on Blob{ text } } } }
  contributionsCollection{ contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } } }
} }
"""


def gql(token: str, login: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-readme-cards"},
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


def ts(iso: str) -> float:
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def collect(user: dict, login: str) -> dict:
    exclude = {n.lower() for n in CONFIG.get("exclude_repos", [])}
    pinned = [n["name"] for n in user["pinnedItems"]["nodes"] if n.get("name")]
    repos = []
    for n in user["repositories"]["nodes"]:
        topics = [t["topic"]["name"] for t in n["repositoryTopics"]["nodes"]]
        if (n["isFork"] or n["isArchived"] or n["isEmpty"] or n.get("isPrivate") or n["name"].lower() == login.lower()
                or n["name"].lower() in exclude or HIDE_TOPIC in topics):
            continue
        progress, tagline = None, None
        try:
            p = json.loads((n.get("portfolio") or {}).get("text") or "null") or {}
            if isinstance(p.get("progress"), (int, float)):
                progress = max(0, min(100, round(p["progress"])))
            if isinstance(p.get("tagline"), str):
                tagline = p["tagline"]
        except (ValueError, AttributeError):
            pass
        ref = n.get("defaultBranchRef") or {}
        commits = (((ref.get("target") or {}).get("history") or {}).get("nodes")) or []
        repos.append({
            "name": n["name"], "description": tagline or n["description"] or "", "url": n["url"], "stars": n["stargazerCount"],
            "pushedAt": n["pushedAt"], "topics": topics, "branch": ref.get("name") or "main",
            "language": (n["primaryLanguage"] or {}).get("name"), "color": (n["primaryLanguage"] or {}).get("color") or VIOLET,
            "commits": [{"sha": c["oid"][:7], "msg": c["messageHeadline"], "at": c["committedDate"]} for c in commits], "progress": progress,
        })
    rank = {name: i for i, name in enumerate(pinned)}
    repos.sort(key=lambda r: (rank.get(r["name"], 99), -ts(r["pushedAt"])))
    featured = next((r for r in repos if FEATURE_TOPICS & set(r["topics"])), None) or max(repos, key=lambda r: r["pushedAt"], default=None)
    if featured:  # featured first in the grid, after any pins
        repos.sort(key=lambda r: (rank.get(r["name"], 99), r is not featured, -ts(r["pushedAt"])))

    days = sorted((d["date"], d["contributionCount"]) for w in user["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"])
    counts = dict(days)
    today = dt.datetime.now(dt.timezone.utc).date()
    d = today if counts.get(today.isoformat(), 0) else today - dt.timedelta(days=1)
    streak = 0
    while counts.get(d.isoformat(), 0) > 0:
        streak += 1
        d -= dt.timedelta(days=1)
    longest = run = 0
    for _, c in days:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    weekly = [sum(c for _, c in days[i : i + 7]) for i in range(0, len(days), 7)]
    langs: dict[str, int] = {}
    for r in repos:
        if r["language"]:
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    top = max(langs, key=langs.get) if langs else "—"
    last = max(repos, key=lambda r: r["pushedAt"], default=None)
    return {
        "repos": repos, "featured": featured, "pinned": pinned,
        "stats": {
            "week": sum(c for _, c in days[-7:]), "bestWeek": max(weekly or [1]) or 1, "year": user["contributionsCollection"]["contributionCalendar"]["totalContributions"],
            "streak": streak, "longest": max(longest, 1), "top": top, "topShare": (langs.get(top, 0) / len(repos)) if repos else 0,
            "last": last, "shown": len(repos),
        },
    }


def now_building_svg(r: dict) -> str:
    W, H = 1200, 270
    css = fonts("inter-800", "inter-400", "mono-400", "mono-700")
    css += (
        "@keyframes lit{0%,100%{opacity:0}4%{opacity:1}14%{opacity:0}}.lit{animation:lit 8s ease-out infinite}"
        "@keyframes head{50%{opacity:.25;transform:scale(1.5)}}.head{transform-box:fill-box;transform-origin:center;animation:head 2.6s ease-in-out infinite}"
        "@keyframes grow{from{transform:scaleX(0)}}.grow{transform-box:fill-box;transform-origin:0 50%;animation:grow 1.4s cubic-bezier(.2,.8,.2,1) .4s backwards}"
    )
    inner = live_dot(40, 42) + label(58, 47, "NOW BUILDING", INK, 13)
    inner += f'<g class="rise" style="animation-delay:.1s"><text x="34" y="104" class="s" font-size="40" font-weight="800" letter-spacing="-.6" fill="#fff">{e(clip(r["name"].replace("-", " ").replace("_", " "), 30))}</text></g>'
    for i, ln in enumerate(wrap(r["description"] or "No description yet.", 62, 2)):
        inner += f'<g class="rise" style="animation-delay:{.2 + i*.05:.2f}s"><text x="36" y="{140 + i*25}" class="s" font-size="18" fill="{INK}" opacity=".86">{e(ln)}</text></g>'
    x = 36
    chips = ""
    seen = set()
    for key, col in [(r["language"], r["color"])] + [TECH.get(t, (t, VIOLET)) for t in r["topics"] if t not in FEATURE_TOPICS]:
        if not key or key.lower() in seen:
            continue
        seen.add(key.lower())
        c, w = chip(x, 182, key, col, 13)
        if x + w > 760:
            break
        chips += c
        x += w + 8
    inner += f'<g class="rise" style="animation-delay:.35s">{chips}</g>'
    if r["progress"] is not None:
        p = r["progress"]
        inner += (
            f'<g class="fade" style="animation-delay:.5s">{label(36, 240, f"BUILD PROGRESS · {p}%", DIM, 11)}'
            f'<rect x="250" y="232" width="420" height="6" rx="3" fill="#fff" fill-opacity=".1"/><rect x="250" y="232" width="{420*p/100:.0f}" height="6" rx="3" fill="url(#vp)" class="grow"/></g>'
        )
    elif r["commits"]:
        c0 = r["commits"][0]
        inner += f'<g class="fade" style="animation-delay:.5s"><text x="36" y="242" class="m" font-size="13.5" fill="{DIM}"><tspan fill="{GREEN}">last commit {e(ago(c0["at"]))}</tspan> — {e(clip(c0["msg"], 64))}</text></g>'

    # Commit timeline: real recent commits, oldest → newest; dots light up left to right, HEAD glows pink.
    commits = list(reversed(r["commits"][:8]))
    X0, X1, Y = 830, 1150, 128
    inner += f'<rect x="800" y="60" width="370" height="160" rx="14" fill="#05060F" fill-opacity=".45" stroke="#fff" stroke-opacity=".08"/>'
    inner += label(820, 88, f'{r["branch"].upper()} · LAST {len(commits)} COMMITS', DIM, 10.5)
    if commits:
        step = (X1 - X0) / max(1, len(commits) - 1)
        inner += f'<line x1="{X0}" x2="{X1}" y1="{Y}" y2="{Y}" stroke="url(#vp)" stroke-width="2" stroke-opacity=".7" class="grow"/>'
        for i, c in enumerate(commits):
            cx = X0 + i * step if len(commits) > 1 else (X0 + X1) / 2
            head = i == len(commits) - 1
            appear = 0.5 + i * 0.12
            lit_delay = 1.6 + i * 0.55
            dot = (
                f'<circle cx="{cx:.0f}" cy="{Y}" r="13" fill="{PINK}" opacity=".3" class="head"/><circle cx="{cx:.0f}" cy="{Y}" r="7" fill="{PINK}" stroke="#F9A8D4" stroke-width="2"/>'
                if head
                else f'<circle cx="{cx:.0f}" cy="{Y}" r="10" fill="{LAV}" opacity="0" class="lit" style="animation-delay:{lit_delay:.2f}s"/>'
                f'<circle cx="{cx:.0f}" cy="{Y}" r="5" fill="#0B0D1F" stroke="{LAV}" stroke-width="2"/>'
            )
            inner += (
                f'<g class="fade" style="animation-delay:{appear:.2f}s">{dot}'
                f'<text x="{cx:.0f}" y="{Y + 30}" text-anchor="middle" class="m" font-size="10" fill="{DIM}">{c["sha"][:4]}</text></g>'
            )
        inner += f'<text x="1150" y="{Y + 68}" text-anchor="end" class="m" font-size="11" fill="{DIM}">HEAD · pushed {e(ago(r["pushedAt"]))}</text>'
    w, h, body = card(W, H, inner, "now-building", text="left")
    return svg(w, h, body, css, "", f'Now building: {r["name"]} — {r["description"]}')


def status_svg(st: dict, stamp: str) -> str:
    W, H = 1200, 236
    css = fonts("inter-800", "mono-400", "mono-700")
    css += "@keyframes grow{from{transform:scaleX(0)}}.grow{transform-box:fill-box;transform-origin:0 50%;animation:grow 1.3s cubic-bezier(.2,.8,.2,1) backwards}"
    live = "LIVE · GITHUB API"
    live_w = len(live) * (11 * MONO_W + 3)  # mono advance + letter-spacing
    inner = label(36, 46, "GITHUB STATS", INK, 13) + live_dot(W - 36 - live_w - 14, 42, 4.5) + label(W - 36, 46, live, GREEN, 11, "end")
    last = st["last"]
    recency = max(0.06, 1 - (dt.datetime.now(dt.timezone.utc).timestamp() - ts(last["pushedAt"])) / (30 * 86400)) if last else 0
    tiles = [
        ("CONTRIBUTIONS · 7 DAYS", str(st["week"]), f'{st["year"]} this year', VIOLET, min(1, st["week"] / st["bestWeek"])),
        ("CURRENT STREAK", f'{st["streak"]}d', f'best {st["longest"]}d', PINK, min(1, st["streak"] / st["longest"])),
        ("TOP LANGUAGE", st["top"], f'{round(st["topShare"]*100)}% of {st["shown"]} repos', BLUE, st["topShare"]),
        ("LAST PUSHED", clip(last["name"], 16) if last else "—", ago(last["pushedAt"]) if last else "", CYAN, recency),
    ]
    for i, (lab, val, sub, col, frac) in enumerate(tiles):
        x = 36 + i * 284
        size = 40 if len(val) <= 8 else (30 if len(val) <= 11 else 24)
        inner += (
            f'<g class="rise" style="animation-delay:{.1 + i*.12:.2f}s"><g transform="translate({x} 70)">'
            f'<rect width="266" height="128" rx="14" fill="#05060F" fill-opacity=".38" stroke="{col}" stroke-opacity=".45"/>'
            f'<text x="20" y="32" class="m" font-size="11" letter-spacing="2" fill="{col}">{e(lab)}</text>'
            f'<text x="20" y="{78 if size == 40 else 74}" class="s" font-size="{size}" font-weight="800" fill="#fff">{e(val)}</text>'
            f'<rect x="20" y="90" width="226" height="3" rx="1.5" fill="#fff" fill-opacity=".1"/>'
            f'<rect x="20" y="90" width="{max(6, 226*frac):.0f}" height="3" rx="1.5" fill="{col}" class="grow" style="animation-delay:{.5 + i*.15:.2f}s"/>'
            f'<text x="20" y="114" class="m" font-size="12.5" fill="{DIM}">{e(sub)}</text></g></g>'
        )
    inner += f'<text x="{W-36}" y="{H-14}" text-anchor="end" class="m" font-size="11" fill="{DIM}" opacity=".8">updated {e(stamp)}</text>'
    w, h, body = card(W, H, inner, "status", text="all")
    alt = f'GitHub stats: {st["week"]} contributions in the last 7 days ({st["year"]} this year), {st["streak"]}-day streak, top language {st["top"]}' + (f', last pushed {last["name"]} {ago(last["pushedAt"])}.' if last else ".")
    return svg(w, h, body, css, "", alt)


def projects_svg(repos: list[dict], featured: str | None, pinned: list[str]) -> str:
    top = repos[:4]
    W = 1200
    rows = max(1, math.ceil(len(top) / 2))
    H = 76 + rows * 172
    css = fonts("inter-700", "inter-400", "mono-400")
    inner = label(36, 46, "PROJECTS · LIVE FROM GITHUB", INK, 13) + label(W - 36, 46, f"{len(repos)} repositories", DIM, 11, "end")
    for i, r in enumerate(top):
        x, y = 36 + (i % 2) * 570, 70 + (i // 2) * 172
        tag = "NOW BUILDING" if r["name"] == featured else ("PINNED" if r["name"] in pinned else "")
        inner += (
            f'<g class="rise" style="animation-delay:{.12 + i*.14:.2f}s"><g transform="translate({x} {y})">'
            f'<rect width="558" height="156" rx="14" fill="#05060F" fill-opacity=".36" stroke="{PINK if tag == "NOW BUILDING" else "#FFFFFF"}" stroke-opacity="{.45 if tag == "NOW BUILDING" else .1}"/>'
            f'<text x="22" y="40" class="s" font-size="21" font-weight="700" fill="#fff">{e(clip(r["name"].replace("-", " ").replace("_", " "), 28 if tag else 36))}</text>'
        )
        if tag:
            inner += f'<rect x="{536 - len(tag)*7.4 - 14:.0f}" y="22" width="{len(tag)*7.4 + 14:.0f}" height="22" rx="11" fill="{PINK}" fill-opacity=".16" stroke="{PINK}" stroke-opacity=".55"/><text x="{536 - 7}" y="37" text-anchor="end" class="m" font-size="10.5" letter-spacing="1.2" fill="#F9A8D4">{tag}</text>'
        for j, ln in enumerate(wrap(r["description"] or "No description yet.", 58, 2)):
            inner += f'<text x="22" y="{72 + j*23}" class="s" font-size="15.5" fill="{INK}" opacity=".78">{e(ln)}</text>'
        inner += (
            f'<circle cx="28" cy="130" r="6" fill="{r["color"]}"/><text x="42" y="135" class="m" font-size="13" fill="{INK}">{e(r["language"] or "—")}</text>'
            f'<text x="536" y="135" text-anchor="end" class="m" font-size="13" fill="{DIM}">★ {r["stars"]}  ·  {e(ago(r["pushedAt"]))}</text></g></g>'
        )
    w, h, body = card(W, H, inner, "projects", text="all")
    return svg(w, h, body, css, "", "Top projects: " + "; ".join(f'{r["name"]} ({r["language"] or "n/a"}, {r["stars"]} stars)' for r in top))


def replace_block(text: str, tag: str, content: str) -> str:
    pattern = re.compile(rf"(<!-- {tag}:START -->)(.*?)(<!-- {tag}:END -->)", re.S)
    return pattern.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text)


def update_readme(path: pathlib.Path, data: dict, login: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text()
    if "<!-- PROJECTS:START -->" not in text and "<!-- NOW:START -->" not in text:
        return False
    cell = lambda t: e(t).replace("|", "\\|")
    rows = [f'| [**{r["name"]}**]({r["url"]}) | {cell(r["description"] or "—")} | {cell(r["language"] or "—")} | ★ {r["stars"]} |' for r in data["repos"]]
    projects = "| Project | What it is | Language | Stars |\n|:--|:--|:--|--:|\n" + "\n".join(rows)
    f = data["featured"]
    raw = f"https://raw.githubusercontent.com/{login}/{login}/output"
    now = f'<a href="{f["url"]}"><img src="{raw}/now-building.svg" width="100%" alt="Now building: {e(f["name"])} — {e(f["description"])}" /></a>' if f else ""
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
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.mode == "static":
        files = {"hero.svg": hero(), "about.svg": about(), "focus.svg": focus(), "tech-stack.svg": tech_stack(), "footer-line.svg": footer()}
    else:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            sys.exit("GITHUB_TOKEN is required")
        data = collect(gql(token, a.user), a.user)
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        files = {"status.svg": status_svg(data["stats"], stamp), "projects.svg": projects_svg(data["repos"], (data["featured"] or {}).get("name"), data["pinned"])}
        if data["featured"]:
            files["now-building.svg"] = now_building_svg(data["featured"])
        if a.readme and update_readme(pathlib.Path(a.readme), data, a.user):
            print("README project links updated")
    for name, content in files.items():
        (out / name).write_text(content)
        print(f"wrote {out / name} ({len(content.encode()) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
