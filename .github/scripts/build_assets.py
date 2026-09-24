#!/usr/bin/env python3
"""Generates every hand-designed, animated SVG used by the profile README.

Run:  python3 .github/scripts/build_assets.py      (writes ./assets/*.svg)
Edit the DATA block below, re-run, commit. No external services, no fonts, no images.
"""
from __future__ import annotations

import math
import pathlib
import random
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "assets"
(OUT / "cards").mkdir(parents=True, exist_ok=True)
(OUT / "sections").mkdir(parents=True, exist_ok=True)

# ── palette ─────────────────────────────────────────────────────────────
BG, PANEL = "#0B0A14", "#12102A"
LAV, PINK, CYAN, MINT = "#A78BFA", "#F472B6", "#8BE9FD", "#86EFAC"
TEXT, MUTED = "#F3EEFF", "#A59CC9"
SANS = "'SF Pro Display','Segoe UI','Helvetica Neue',Arial,sans-serif"
MONO = "'JetBrains Mono','SF Mono','Cascadia Code',Menlo,Consolas,monospace"
SERIF = "Georgia,'Times New Roman',serif"


def e(s: str) -> str:
    return escape(s)


def svg(w: int, h: int, body: str, defs: str = "", css: str = "") -> str:
    style = f"<style>{css}</style>" if css else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'font-family="{SANS}">{style}<defs>{defs}'
        f'<linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{LAV}"/>'
        f'<stop offset="1" stop-color="{PINK}"/></linearGradient>'
        f'<linearGradient id="gv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{LAV}"/>'
        f'<stop offset="1" stop-color="{PINK}"/></linearGradient>'
        f'<clipPath id="clip"><rect width="{w}" height="{h}" rx="22"/></clipPath></defs>'
        f'<g clip-path="url(#clip)">{body}</g></svg>'
    )


def stars(seed: int, n: int, w: int, h: int, x0: int = 0) -> str:
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        x, y = x0 + rnd.random() * (w - x0), rnd.random() * h
        r = rnd.choice([0.8, 1, 1.2, 1.6])
        c = rnd.choice([LAV, PINK, CYAN, "#FFFFFF"])
        d = 2 + rnd.random() * 4
        out.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{c}" opacity=".2">'
            f'<animate attributeName="opacity" values=".1;.9;.1" dur="{d:.1f}s" begin="{rnd.random()*4:.1f}s" repeatCount="indefinite"/></circle>'
        )
    return "".join(out)


def backdrop(w: int, h: int, seed: int = 1, glow_a=(0.18, 0.2), glow_b=(0.85, 0.85)) -> str:
    """Panel background: deep gradient, faint grid, two drifting glows, twinkling stars."""
    ax, ay = glow_a[0] * w, glow_a[1] * h
    bx, by = glow_b[0] * w, glow_b[1] * h
    return f"""
<defs>
  <linearGradient id="bg{seed}" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{BG}"/><stop offset=".55" stop-color="#171033"/><stop offset="1" stop-color="{BG}"/>
  </linearGradient>
  <radialGradient id="ga{seed}"><stop offset="0" stop-color="{LAV}" stop-opacity=".38"/><stop offset="1" stop-color="{LAV}" stop-opacity="0"/></radialGradient>
  <radialGradient id="gb{seed}"><stop offset="0" stop-color="{PINK}" stop-opacity=".30"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient>
  <pattern id="grid{seed}" width="36" height="36" patternUnits="userSpaceOnUse"><path d="M36 0H0V36" fill="none" stroke="{LAV}" stroke-opacity=".07"/></pattern>
</defs>
<rect width="{w}" height="{h}" fill="url(#bg{seed})"/>
<rect width="{w}" height="{h}" fill="url(#grid{seed})"/>
<circle cx="{ax:.0f}" cy="{ay:.0f}" r="{h*0.75:.0f}" fill="url(#ga{seed})">
  <animateTransform attributeName="transform" type="translate" values="0 0;40 24;0 0" dur="14s" repeatCount="indefinite"/></circle>
<circle cx="{bx:.0f}" cy="{by:.0f}" r="{h*0.7:.0f}" fill="url(#gb{seed})">
  <animateTransform attributeName="transform" type="translate" values="0 0;-36 -20;0 0" dur="17s" repeatCount="indefinite"/></circle>
{stars(seed, int(w * h / 9000), w, h)}
"""


def border(w: int, h: int, rx: int = 22) -> str:
    return (
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="{rx}" fill="none" stroke="url(#g)" stroke-opacity=".55" stroke-width="1.5"/>'
    )


# ── stylised face made of landmark dots + a procedural mesh ─────────────
def face_points() -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in range(30):  # head / jaw contour
        a = 2 * math.pi * i / 30
        pts.append((80 * math.cos(a), 105 * math.sin(a)))
    for sx in (-1, 1):  # brows
        for k in range(5):
            t = k / 4
            pts.append((sx * (58 - 40 * t), -42 - 9 * math.sin(math.pi * t)))
    for sx in (-1, 1):  # eyes
        for k in range(8):
            a = 2 * math.pi * k / 8
            pts.append((sx * 36 + 15 * math.cos(a), -22 + 6 * math.sin(a)))
    pts += [(0, -20), (0, -4), (0, 12), (-9, 30), (-4, 33), (0, 34), (4, 33), (9, 30)]  # nose
    for k in range(7):  # upper lip
        t = k / 6
        pts.append((-24 + 48 * t, 58 - 6 * math.sin(math.pi * t)))
    for k in range(5):  # lower lip
        t = (k + 1) / 6
        pts.append((-24 + 48 * t, 60 + 8 * math.sin(math.pi * t)))
    return pts


def face(scale: float = 1.0, uid: str = "f", dots_opacity: float = 0.95) -> str:
    pts = face_points()
    lines, dots = [], []
    for i, (x1, y1) in enumerate(pts):
        near = sorted(
            ((math.hypot(x1 - x2, y1 - y2), j) for j, (x2, y2) in enumerate(pts) if j > i),
            key=lambda t: t[0],
        )[:2]
        for d, j in near:
            if d < 44:
                x2, y2 = pts[j]
                lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    for i, (x, y) in enumerate(pts):
        c = PINK if i % 11 == 0 else (CYAN if i % 7 == 0 else LAV)
        dots.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.3" fill="{c}">'
            f'<animate attributeName="opacity" values=".35;{dots_opacity};.35" dur="3.2s" begin="{(i*0.07)%3:.2f}s" repeatCount="indefinite"/></circle>'
        )
    return (
        f'<g transform="scale({scale})"><g stroke="{LAV}" stroke-opacity=".28" stroke-width=".8">{"".join(lines)}</g>{"".join(dots)}</g>'
    )


def viewfinder(w: float, h: float, color: str = CYAN, arm: float = 22) -> str:
    x0, y0, x1, y1 = -w / 2, -h / 2, w / 2, h / 2
    p = ""
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        p += f'M{cx + dx*arm:.0f} {cy:.0f}H{cx:.0f}V{cy + dy*arm:.0f}'
    return f'<path d="{p}" fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" opacity=".9"/>'


def scan(w: float, h: float, uid: str, dur: float = 3.6, delay: float = 0) -> str:
    return f"""
<defs><linearGradient id="sc{uid}" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset="1" stop-color="{CYAN}" stop-opacity=".38"/></linearGradient></defs>
<rect x="{-w/2:.0f}" width="{w:.0f}" height="46" fill="url(#sc{uid})"><animate attributeName="y" values="{-h/2-46:.0f};{h/2-46:.0f};{-h/2-46:.0f}" dur="{dur}s" begin="{delay}s" repeatCount="indefinite"/></rect>
<rect x="{-w/2:.0f}" width="{w:.0f}" height="2.4" fill="{CYAN}" opacity=".95"><animate attributeName="y" values="{-h/2:.0f};{h/2:.0f};{-h/2:.0f}" dur="{dur}s" begin="{delay}s" repeatCount="indefinite"/></rect>"""


def pill(x: float, y: float, w: float, text: str, color: str, dot: bool = True, size: int = 13) -> str:
    d = (
        f'<circle cx="{x+15}" cy="{y+13}" r="4" fill="{color}"><animate attributeName="opacity" values="1;.25;1" dur="1.8s" repeatCount="indefinite"/></circle>'
        if dot
        else ""
    )
    tx = x + (28 if dot else w / 2)
    anchor = "start" if dot else "middle"
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="13" fill="{color}" fill-opacity=".13" stroke="{color}" stroke-opacity=".6"/>{d}'
        f'<text x="{tx}" y="{y+18}" font-family="{MONO}" font-size="{size}" font-weight="600" letter-spacing="1.2" fill="{color}" text-anchor="{anchor}">{e(text)}</text>'
    )


def tags(x: float, y: float, items: list[str], color: str = MUTED) -> str:
    out, cx = [], x
    for t in items:
        w = 14 + len(t) * 8.1
        out.append(
            f'<rect x="{cx:.0f}" y="{y}" width="{w:.0f}" height="26" rx="8" fill="#FFFFFF" fill-opacity=".05" stroke="{LAV}" stroke-opacity=".28"/>'
            f'<text x="{cx+w/2:.0f}" y="{y+18}" font-family="{MONO}" font-size="12.5" fill="{color}" text-anchor="middle">{e(t)}</text>'
        )
        cx += w + 8
    return "".join(out)


def write(path: pathlib.Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    print("wrote", path.relative_to(ROOT), f"{len(content)//1024 or 1} KB")


# ═══════════════════════════════ HERO ═══════════════════════════════════
def hero() -> str:
    W, H = 1000, 400
    body = backdrop(W, H, seed=1, glow_a=(0.2, 0.3), glow_b=(0.85, 0.75))
    body += f"""
<defs>
  <linearGradient id="nameg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{LAV}"/><stop offset=".55" stop-color="{PINK}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
  <linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".85"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <mask id="nm"><text x="52" y="188" font-size="84" font-weight="800" fill="#fff" letter-spacing="-1">Yuvika</text>
     <text x="52" y="268" font-size="84" font-weight="800" fill="#fff" letter-spacing="-1">Malhotra</text></mask>
</defs>
<text x="54" y="98" font-family="{MONO}" font-size="14.5" letter-spacing="4.5" fill="{CYAN}">✦ AI &amp; MACHINE LEARNING · FINAL-YEAR CS</text>
<g mask="url(#nm)">
  <rect x="40" y="90" width="520" height="200" fill="url(#nameg)"/>
  <rect x="-200" y="90" width="120" height="200" fill="url(#shine)" transform="skewX(-18)"><animate attributeName="x" values="-200;700" dur="5.5s" repeatCount="indefinite"/></rect>
</g>
<text x="54" y="316" font-family="{SERIF}" font-style="italic" font-size="23" fill="#E9D5FF">I build things that see, reason, and ship.</text>
{pill(54, 344, 300, "OPEN TO AI/ML OPPORTUNITIES", MINT)}
<g transform="translate(790 200)">
  <ellipse rx="135" ry="150" fill="none" stroke="{LAV}" stroke-opacity=".18" stroke-dasharray="3 9"><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="60s" repeatCount="indefinite"/></ellipse>
  {viewfinder(210, 270)}
  {face(1.0, "h")}
  {scan(210, 270, "h")}
  <text y="166" text-anchor="middle" font-family="{MONO}" font-size="12.5" letter-spacing="3" fill="{CYAN}">LIVENESS CHECK<animate attributeName="opacity" values="1;.35;1" dur="3s" repeatCount="indefinite"/></text>
</g>
{border(W, H, 24)}
"""
    return svg(W, H, body)


# ═══════════════════════════ SECTION HEADERS ════════════════════════════
def section(idx: str, title: str, sub: str) -> str:
    W, H = 1000, 74
    tw = 30 + len(title) * 17
    lx0, lx1 = 70 + tw + 34, W - len(sub) * 10 - 40
    body = f"""
<rect x="2" y="14" width="50" height="40" rx="12" fill="{LAV}" fill-opacity=".12" stroke="url(#g)" stroke-width="1.4"/>
<text x="27" y="41" text-anchor="middle" font-family="{MONO}" font-size="17" font-weight="700" fill="{PINK}">{idx}</text>
<text x="70" y="43" font-size="29" font-weight="750" fill="{TEXT}" letter-spacing=".3">{e(title)}</text>
<text x="{70+tw}" y="42" font-size="20" fill="{PINK}">✦</text>
<text x="{W-4}" y="42" text-anchor="end" font-family="{MONO}" font-size="13" letter-spacing="2" fill="{MUTED}">{e(sub.upper())}</text>
<line x1="{lx0}" y1="37" x2="{lx1}" y2="37" stroke="#A78BFA" stroke-opacity=".55" stroke-width="1.6" stroke-dasharray="2 7"/>
<circle r="4" fill="{CYAN}"><animateMotion dur="4.5s" repeatCount="indefinite" path="M{lx0} 37 L{lx1} 37"/></circle>
"""
    return svg(W, H, body)


# ═════════════════════════ ABOUT — "MODEL CARD" ═════════════════════════
def model_card() -> str:
    rows = [
        ("task", "computer vision  ·  LLM systems  ·  full-stack apps", LAV),
        ("backbone", "Python · PyTorch · FastAPI · React", LAV),
        ("trained_on", "Computer Science, AI & ML specialisation  ·  final year", LAV),
        ("fine_tuning", "OptiLLM (LLM gateway)  ·  Anti-Spoof (face liveness)", PINK),
        ("deployed", "CodeShelf — web app + mobile app, live", CYAN),
        ("evaluation", "numbers published only after they are measured", MINT),
        ("intended_use", "AI/ML internships and full-time roles", LAV),
        ("contact", "yuvikamalhotra1414@gmail.com", CYAN),
    ]
    W = 1000
    H = 96 + len(rows) * 38 + 16
    css = "".join(
        f".r{i}{{animation:in .6s ease-out {0.15*i+0.2:.2f}s backwards}}" for i in range(len(rows))
    ) + "@keyframes in{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:none}}"
    body = backdrop(W, H, seed=2, glow_a=(0.1, 0.1), glow_b=(0.95, 0.9))
    body += f"""
<text x="36" y="52" font-family="{MONO}" font-size="15" letter-spacing="3" fill="{MUTED}">MODEL CARD</text>
<text x="176" y="52" font-family="{MONO}" font-size="15" letter-spacing="1" fill="{PINK}">yuvika-malhotra · v2026</text>
{pill(W-206, 32, 170, "AVAILABLE", MINT)}
<line x1="36" y1="72" x2="{W-36}" y2="72" stroke="{LAV}" stroke-opacity=".3"/>
"""
    for i, (k, v, c) in enumerate(rows):
        y = 112 + i * 38
        body += (
            f'<g class="r{i}"><text x="36" y="{y}" font-family="{MONO}" font-size="16" fill="{MUTED}">{k}</text>'
            f'<text x="220" y="{y}" font-family="{MONO}" font-size="16" fill="{c}">{e(v)}</text></g>'
        )
    body += border(W, H)
    return svg(W, H, body, css=css)


# ═══════════════════════════ FEATURED PROJECT CARDS ═════════════════════
def flagship(uid: str, seed: int, title: str, tagline: list[str], status: str, scolor: str, chips: list[str], viz: str, hint: str) -> str:
    W, H = 1000, 300
    body = backdrop(W, H, seed=seed, glow_a=(0.15, 0.3), glow_b=(0.85, 0.7))
    body += pill(40, 34, 40 + len(status) * 9.4, status, scolor)
    body += f'<text x="40" y="112" font-size="42" font-weight="800" fill="{TEXT}" letter-spacing="-.5">{e(title)}</text>'
    for i, line in enumerate(tagline):
        body += f'<text x="40" y="{150+i*25}" font-size="17" fill="{MUTED}">{e(line)}</text>'
    body += tags(40, 222, chips)
    body += f'<text x="40" y="272" font-family="{MONO}" font-size="13.5" letter-spacing="1.5" fill="{PINK}">{e(hint)}  →</text>'
    body += f'<line x1="500" y1="40" x2="500" y2="{H-40}" stroke="{LAV}" stroke-opacity=".18" stroke-dasharray="2 6"/>'
    body += viz
    body += border(W, H)
    return svg(W, H, body)


def optillm_viz() -> str:
    def node(x, y, w, h, label, color, r=12):
        return (
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{color}" fill-opacity=".14" stroke="{color}" stroke-opacity=".8" stroke-width="1.5"/>'
            f'<text x="{x+w/2}" y="{y+h/2+5}" text-anchor="middle" font-family="{MONO}" font-size="13" font-weight="600" fill="{color}">{label}</text>'
        )

    paths = {
        "in": "M74 150H146",
        "hit": "M208 112C208 50 74 50 54 126",
        "c2r": "M270 150H312",
        "small": "M352 150C374 150 380 100 400 100",
        "large": "M352 150C374 150 380 200 400 200",
    }
    g = '<g transform="translate(500 0)">'
    g += "".join(f'<path d="{d}" fill="none" stroke="{LAV}" stroke-opacity=".28" stroke-width="1.6" stroke-dasharray="4 6"/>' for d in paths.values())
    g += f'<circle cx="54" cy="150" r="22" fill="{LAV}" fill-opacity=".14" stroke="{LAV}" stroke-width="1.5"/><text x="54" y="155" text-anchor="middle" font-family="{MONO}" font-size="12.5" fill="{LAV}">app</text>'
    g += node(146, 118, 124, 64, "semantic cache", CYAN)
    g += node(312, 128, 40, 44, "", PINK, 22) + f'<text x="332" y="192" text-anchor="middle" font-family="{MONO}" font-size="11" fill="{PINK}">router</text>'
    g += node(400, 80, 72, 40, "mini", LAV)
    g += node(400, 180, 72, 40, "large", PINK)
    g += f'<circle r="5.5" fill="{PINK}"><animateMotion dur="3.8s" repeatCount="indefinite" begin="0s" path="M74 150H146H270H312H352C374 150 380 200 400 200"/></circle>'
    g += f'<circle r="5.5" fill="{LAV}"><animateMotion dur="3.8s" repeatCount="indefinite" begin="1.3s" path="M74 150H146H270H312H352C374 150 380 100 400 100"/></circle>'
    g += f'<circle r="5.5" fill="{CYAN}"><animateMotion dur="2.4s" repeatCount="indefinite" begin=".6s" path="M74 150H146L208 118C208 50 74 50 54 128"/></circle>'
    g += f'<text x="20" y="240" font-family="{MONO}" font-size="11.5" fill="{CYAN}">● hit → answered instantly</text>'
    g += f'<text x="20" y="262" font-family="{MONO}" font-size="11.5" fill="{PINK}">● miss → routed by complexity</text>'
    g += "</g>"
    return g


def antispoof_viz() -> str:
    g = "<g>"
    g += f'<g transform="translate(640 152) scale(.6)">{viewfinder(210, 270)}{face(1.0, "a1")}{scan(210, 270, "a1", 3.6)}</g>'
    g += f'<text x="640" y="262" text-anchor="middle" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{MUTED}">CAMERA</text>'
    g += (
        f'<g><rect x="606" y="18" width="68" height="26" rx="13" fill="{MINT}" fill-opacity=".14" stroke="{MINT}"/>'
        f'<text x="640" y="36" text-anchor="middle" font-family="{MONO}" font-size="13" font-weight="700" fill="{MINT}">✓ LIVE</text>'
        f'<animate attributeName="opacity" values="1;1;.25;.25;1" keyTimes="0;.45;.55;.95;1" dur="7.2s" repeatCount="indefinite"/></g>'
    )
    g += (
        f'<defs><clipPath id="ph"><rect x="-58" y="-88" width="116" height="176" rx="12"/></clipPath></defs>'
        f'<g transform="translate(850 152)"><rect x="-66" y="-100" width="132" height="200" rx="18" fill="#0B0A14" stroke="{PINK}" stroke-opacity=".75" stroke-width="2"/>'
        f'<rect x="-22" y="-93" width="44" height="5" rx="2.5" fill="{PINK}" fill-opacity=".5"/>'
        f'<g clip-path="url(#ph)"><g transform="scale(.5)">{face(1.0, "a2", .8)}</g>{scan(116, 176, "a2", 3.6, 0)}</g></g>'
    )
    g += f'<text x="850" y="270" text-anchor="middle" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{MUTED}">SCREEN REPLAY</text>'
    g += (
        f'<g><rect x="812" y="18" width="76" height="26" rx="13" fill="{PINK}" fill-opacity=".14" stroke="{PINK}"/>'
        f'<text x="850" y="36" text-anchor="middle" font-family="{MONO}" font-size="13" font-weight="700" fill="{PINK}">✕ SPOOF</text>'
        f'<animate attributeName="opacity" values=".25;.25;1;1;.25" keyTimes="0;.45;.55;.95;1" dur="7.2s" repeatCount="indefinite"/></g>'
    )
    return g + "</g>"


def codeshelf_viz() -> str:
    # forgetting curve that is re-strengthened by each review (spaced repetition)
    X0, Y0, X1, Y1 = 548, 60, 950, 218
    pts, t, s = [], 0.0, 1.0
    reviews = [0.0, 1.0, 3.2, 7.0, 15.0, 30.0]
    total = 34.0
    strength = 1.4
    for ri, rt in enumerate(reviews):
        nxt = reviews[ri + 1] if ri + 1 < len(reviews) else total
        steps = 26
        for k in range(steps + 1):
            tt = rt + (nxt - rt) * k / steps
            r = math.exp(-(tt - rt) / strength)
            pts.append((tt, r))
        strength *= 2.35
    xs = lambda tt: X0 + (X1 - X0) * (tt / total) ** 0.62
    ys = lambda r: Y1 - (Y1 - Y0) * r
    d = "M" + " L".join(f"{xs(a):.1f} {ys(b):.1f}" for a, b in pts)
    g = f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="{LAV}" stroke-opacity=".35"/><line x1="{X0}" y1="{Y0-10}" x2="{X0}" y2="{Y1}" stroke="{LAV}" stroke-opacity=".35"/>'
    g += f'<path d="{d}" fill="none" stroke="url(#g)" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"><animate attributeName="stroke-dashoffset" values="1;0;0;1" keyTimes="0;.6;.92;1" dur="8s" repeatCount="indefinite"/></path>'
    for i, rt in enumerate(reviews):
        cx = xs(rt)
        g += (
            f'<g><circle cx="{cx:.1f}" cy="{ys(1):.1f}" r="6" fill="{CYAN}"/><circle cx="{cx:.1f}" cy="{ys(1):.1f}" r="11" fill="none" stroke="{CYAN}" stroke-opacity=".5"/>'
            f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;{0.05+0.1*i:.2f};{0.1+0.1*i:.2f};.92;1" dur="8s" repeatCount="indefinite"/></g>'
        )
    g += f'<text x="{X0}" y="{Y1+24}" font-family="{MONO}" font-size="12" letter-spacing="1.5" fill="{MUTED}">day 0 → each review pushes forgetting further out</text>'
    g += f'<text x="{X0}" y="{Y0-22}" font-family="{MONO}" font-size="12" letter-spacing="1.5" fill="{PINK}">RETENTION</text>'
    g += f'<text x="{X1}" y="{Y1-14}" text-anchor="end" font-family="{MONO}" font-size="11.5" fill="{PINK}" fill-opacity=".85">↑ review just before you forget</text>'
    return g


# ════════════════════════════ SMALL PROJECT CARDS ═══════════════════════
def small(uid: str, seed: int, title: str, desc: list[str], chips: list[str], viz: str) -> str:
    W, H = 326, 300
    body = backdrop(W, H, seed=seed, glow_a=(0.2, 0.15), glow_b=(0.9, 0.9))
    body += viz
    body += f'<text x="26" y="176" font-size="22" font-weight="800" fill="{TEXT}">{e(title)}</text>'
    for i, line in enumerate(desc):
        body += f'<text x="26" y="{202+i*20}" font-size="14" fill="{MUTED}">{e(line)}</text>'
    body += tags(26, 254, chips)
    body += border(W, H, 20)
    return svg(W, H, body)


def crowd_viz() -> str:
    rnd = random.Random(5)
    g = f'<g transform="translate(0 0)"><rect x="26" y="26" width="274" height="120" rx="14" fill="#FFFFFF" fill-opacity=".03" stroke="{LAV}" stroke-opacity=".25"/>'
    for i in range(46):
        x, y = 40 + rnd.random() * 246, 40 + rnd.random() * 92
        g += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="2" fill="{LAV}" fill-opacity=".8"/>'
    for cx, cy, r, c, d in ((110, 80, 46, PINK, 3.4), (210, 92, 38, LAV, 4.2), (170, 58, 28, CYAN, 3.0)):
        g += (
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{c}" fill-opacity=".22"><animate attributeName="r" values="{r-6};{r+6};{r-6}" dur="{d}s" repeatCount="indefinite"/>'
            f'<animate attributeName="fill-opacity" values=".12;.34;.12" dur="{d}s" repeatCount="indefinite"/></circle>'
        )
    return g + "</g>"


def bot_viz() -> str:
    rnd = random.Random(9)
    nodes = [(50 + rnd.random() * 226, 44 + rnd.random() * 90) for _ in range(20)]
    flagged = {3, 9, 14}
    g = '<g>'
    for i, (x, y) in enumerate(nodes):
        for j in (i + 1, i + 3):
            if j < len(nodes) and math.hypot(x - nodes[j][0], y - nodes[j][1]) < 90:
                g += f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{nodes[j][0]:.0f}" y2="{nodes[j][1]:.0f}" stroke="{LAV}" stroke-opacity=".22"/>'
    for i, (x, y) in enumerate(nodes):
        if i in flagged:
            g += (
                f'<circle cx="{x:.0f}" cy="{y:.0f}" r="7" fill="{PINK}"/><circle cx="{x:.0f}" cy="{y:.0f}" r="7" fill="none" stroke="{PINK}"><animate attributeName="r" values="7;20;7" dur="2.6s" begin="{i*0.2:.1f}s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values=".9;0;.9" dur="2.6s" begin="{i*0.2:.1f}s" repeatCount="indefinite"/></circle>'
            )
        else:
            g += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="4.5" fill="{LAV}" fill-opacity=".85"/>'
    return g + "</g>"


def pose_viz() -> str:
    # animated skeleton doing a squat-like motion via a moving hip/knee joints
    j = lambda x, y: (x, y)
    g = f'<g transform="translate(163 88)" stroke="{LAV}" stroke-width="3" stroke-linecap="round" fill="none">'
    g += f'<circle cx="0" cy="-54" r="10" fill="{PINK}" stroke="none"/>'
    g += '<path d="M0 -42 V 6"/><path d="M0 -30 L -30 -8"/><path d="M0 -30 L 30 -8"/>'
    g += (
        f'<path d="M0 6 L -20 34 L -20 62"><animate attributeName="d" values="M0 6 L -20 34 L -20 62;M0 20 L -30 40 L -20 62;M0 6 L -20 34 L -20 62" dur="3s" repeatCount="indefinite"/></path>'
        f'<path d="M0 6 L 20 34 L 20 62"><animate attributeName="d" values="M0 6 L 20 34 L 20 62;M0 20 L 30 40 L 20 62;M0 6 L 20 34 L 20 62" dur="3s" repeatCount="indefinite"/></path>'
    )
    g += "</g>"
    for x, y in ((163, 88 - 42), (133, 80), (193, 80), (163, 94)):
        g += f'<circle cx="{x}" cy="{y}" r="4.5" fill="{CYAN}"/>'
    return g


# ════════════════════════════════ STACK ═════════════════════════════════
def stack() -> str:
    groups = [
        ("LANGUAGES", LAV, ["Python", "JavaScript", "C++", "SQL"]),
        ("ML / VISION", PINK, ["PyTorch", "OpenCV", "MediaPipe", "scikit-learn", "XGBoost", "Hugging Face"]),
        ("BUILD", CYAN, ["FastAPI", "React", "Next.js", "Streamlit", "Expo / React Native"]),
        ("DATA & SHIP", MINT, ["PostgreSQL", "Docker", "GitHub Actions", "Vercel", "Render", "Git"]),
    ]
    W = 1000
    H = 40 + len(groups) * 62
    body = backdrop(W, H, seed=7, glow_a=(0.1, 0.2), glow_b=(0.9, 0.8))
    for gi, (name, col, items) in enumerate(groups):
        y = 34 + gi * 62
        body += f'<text x="34" y="{y+22}" font-family="{MONO}" font-size="13" letter-spacing="3" fill="{col}">{e(name)}</text>'
        cx = 176
        for k, it in enumerate(items):
            w = 48 + len(it) * 8.8
            body += (
                f'<g><rect x="{cx}" y="{y}" width="{w}" height="34" rx="17" fill="{col}" fill-opacity=".10" stroke="{col}" stroke-opacity=".55"/>'
                f'<circle cx="{cx+16}" cy="{y+17}" r="3.5" fill="{col}"><animate attributeName="opacity" values=".35;1;.35" dur="3.4s" begin="{(gi*6+k)*0.25:.2f}s" repeatCount="indefinite"/></circle>'
                f'<text x="{cx+28}" y="{y+22}" font-size="15" font-weight="600" fill="{TEXT}">{e(it)}</text></g>'
            )
            cx += w + 9
    body += border(W, H)
    return svg(W, H, body)


# ════════════════════════════ CONNECT / FOOTER ══════════════════════════
def connect() -> str:
    W, H = 1000, 170
    body = backdrop(W, H, seed=8, glow_a=(0.2, 0.5), glow_b=(0.85, 0.5))
    body += f'<text x="{W/2}" y="74" text-anchor="middle" font-family="{SERIF}" font-style="italic" font-size="34" fill="#F5E9FF">Let’s build something that ships.</text>'
    body += f'<text x="{W/2}" y="112" text-anchor="middle" font-family="{MONO}" font-size="14" letter-spacing="3" fill="{MUTED}">INTERNSHIPS · FULL-TIME · COLLABS</text>'
    body += f'<text x="{W/2-300}" y="70" font-size="20" fill="{PINK}">✦<animate attributeName="opacity" values="1;.2;1" dur="2.4s" repeatCount="indefinite"/></text>'
    body += f'<text x="{W/2+288}" y="118" font-size="20" fill="{CYAN}">✦<animate attributeName="opacity" values=".2;1;.2" dur="2.4s" repeatCount="indefinite"/></text>'
    body += border(W, H)
    return svg(W, H, body)


def footer() -> str:
    W, H = 1000, 130
    waves = ""
    for i, (c, op, amp, dur) in enumerate(((LAV, .35, 16, 9), (PINK, .3, 12, 12), (CYAN, .2, 9, 15))):
        base = 78 + i * 12
        d1 = f"M-250 {base} " + " ".join(f"Q{x+62} {base-amp} {x+125} {base} T{x+250} {base}" for x in range(-250, 1500, 250)) + f" V{H} H-250Z"
        waves += f'<path d="{d1}" fill="{c}" fill-opacity="{op}"><animateTransform attributeName="transform" type="translate" values="0 0;-125 0;0 0" dur="{dur}s" repeatCount="indefinite"/></path>'
    body = f'<rect width="{W}" height="{H}" fill="{BG}"/>{stars(3, 30, W, 80)}{waves}'
    body += f'<text x="{W/2}" y="52" text-anchor="middle" font-family="{MONO}" font-size="13" letter-spacing="3" fill="{MUTED}">DESIGNED &amp; GENERATED WITH PYTHON  ·  ✦  ·  UPDATED BY GITHUB ACTIONS</text>'
    return svg(W, H, body)


def main() -> None:
    write(OUT / "hero.svg", hero())
    for i, (title, sub) in enumerate(
        [("about", "the short version"), ("building now", "in progress"), ("shipped", "live & deployed"),
         ("more work", "selected projects"), ("stack", "what I actually use"), ("live from github", "generated, not typed"),
         ("say hi", "open to work")]
    ):
        write(OUT / "sections" / f"{i+1:02d}-{title.split()[0]}.svg", section(f"{i+1:02d}", title, sub))
    write(OUT / "about.svg", model_card())
    write(
        OUT / "cards" / "optillm.svg",
        flagship("o", 11, "OptiLLM", ["An AI gateway between your app and the LLM:", "semantic cache, complexity-based model routing,", "prompt optimiser and per-request cost analytics."],
                 "IN PROGRESS", PINK, ["FastAPI", "Next.js", "PostgreSQL", "Docker"], optillm_viz(), "github.com/Yuvika687/OptiLLM"),
    )
    write(
        OUT / "cards" / "antispoof.svg",
        flagship("a", 12, "Anti-Spoof Attendance", ["A mask-aware liveness gate in front of face", "recognition: blocks printed photos and screen", "replays. MediaPipe detector + CNN classifier."],
                 "IN PROGRESS", PINK, ["PyTorch", "MediaPipe", "OpenCV", "ONNX"], antispoof_viz(), "github.com/Yuvika687/anti-spoof-attendance"),
    )
    write(
        OUT / "cards" / "codeshelf.svg",
        flagship("c", 13, "CodeShelf", ["Spaced-repetition for developers. Turn notes,", "mistakes and solved problems into revision cards.", "Web app + Expo mobile app, JWT auth, tag search."],
                 "SHIPPED · LIVE", MINT, ["React", "FastAPI", "PostgreSQL", "Expo"], codeshelf_viz(), "code-shelf-eight.vercel.app"),
    )
    write(OUT / "cards" / "crowd.svg", small("s", 21, "SafeCrowd Vision", ["Unsupervised crowd-density", "segmentation for event safety."], ["OpenCV", "PyTorch", "Streamlit"], crowd_viz()))
    write(OUT / "cards" / "bot.svg", small("b", 22, "Bot Detector", ["Supervised model that flags", "fake Twitter/X accounts."], ["XGBoost", "Streamlit", "FastAPI"], bot_viz()))
    write(OUT / "cards" / "fitness.svg", small("f", 23, "AI Fitness Coach", ["Workout and diet planning with", "pose-based form feedback."], ["FastAPI", "Gemini", "MediaPipe"], pose_viz()))
    write(OUT / "stack.svg", stack())
    write(OUT / "connect.svg", connect())
    write(OUT / "footer.svg", footer())


if __name__ == "__main__":
    main()
