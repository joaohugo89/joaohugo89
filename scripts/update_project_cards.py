#!/usr/bin/env python3
"""
Gera os cards de projeto do README a partir dos repositórios com estrela do usuário.

Regra: repositórios que o usuário marcou com estrela E que pertencem a ele,
ordenados pelo último push (mais recente primeiro), limitados a MAX_CARDS.

Saída:
  assets/cards/repo-1.svg ... repo-N.svg
  bloco entre <!-- PROJECTS:START --> e <!-- PROJECTS:END --> no README.md

Só usa a biblioteca padrão do Python. Roda via .github/workflows/update-cards.yml.
"""
import base64
import json
import math
import os
import random
import re
import sys
import urllib.request
from datetime import datetime
from html import escape as E
from pathlib import Path

USER = os.environ.get("GH_USER", "joaohugo89")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
MAX_CARDS = int(os.environ.get("MAX_CARDS", "4"))
OWN_ONLY = os.environ.get("OWN_ONLY", "true").lower() == "true"

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
CARDS = ROOT / "assets" / "cards"
FONTS = ROOT / "assets" / "fonts"
START, END = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"

WHITE, B1, B2, B3, B4, BG = "#ffffff", "#1d4ed8", "#2563eb", "#93c5fd", "#60a5fa", "#070b14"
W, H = 600, 230


# ---------------------------------------------------------------- GitHub API
def api(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USER}-readme-cards",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r), r.headers.get("Link", "")


def starred_repos():
    url = f"https://api.github.com/users/{USER}/starred?per_page=100&sort=updated&direction=desc"
    repos = []
    while url:
        page, link = api(url)
        repos += page
        m = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = m.group(1) if m else None
    return repos


def pick(repos):
    if OWN_ONLY:
        repos = [r for r in repos if r["owner"]["login"].lower() == USER.lower()]
    repos = [r for r in repos if not r.get("archived")]
    repos.sort(key=lambda r: r.get("pushed_at") or "", reverse=True)
    return repos[:MAX_CARDS]


# ---------------------------------------------------------------- lightning
def bolt(x1, y1, x2, y2, disp, rng, detail=2):
    pts, d = [(x1, y1), (x2, y2)], disp
    while d > detail:
        new = [pts[0]]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            dx, dy = bx - ax, by - ay
            L = math.hypot(dx, dy) or 1
            off = rng.uniform(-d, d)
            new += [((ax + bx) / 2 - dy / L * off, (ay + by) / 2 + dx / L * off), (bx, by)]
        pts, d = new, d / 2
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def font_face(weight):
    data = base64.b64encode((FONTS / f"orbitron-{weight}.woff2").read_bytes()).decode()
    return f"@font-face{{font-family:'Orb{weight}';src:url(data:font/woff2;base64,{data}) format('woff2');}}"


# ---------------------------------------------------------------- text helpers
def pretty(name):
    return re.sub(r"[-_]+", " ", name).strip().upper()


def wrap(text, n, max_lines=3):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + len(w) + 1 > n:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: n - 1].rstrip() + "…"
    return lines


def title_size(text, max_w=470, base=26):
    # largura aproximada da Orbitron 700 em caixa alta + letter-spacing de 3px
    est = lambda s: len(text) * (0.86 * s + 3)
    size = base
    while size > 16 and est(size) > max_w:
        size -= 1
    if est(size) > max_w:  # ainda grande: corta
        keep = int(max_w / (0.86 * size + 3)) - 1
        text = text[:keep].rstrip() + "…"
    return text, size


def ago(iso):
    if not iso:
        return ""
    d = datetime.strptime(iso[:10], "%Y-%m-%d")
    return d.strftime("%b %Y").upper()


# ---------------------------------------------------------------- card
def card(idx, repo):
    name, size = title_size(pretty(repo["name"]))
    desc = repo.get("description") or "No description yet."
    lang = (repo.get("language") or "").upper()
    stars = repo.get("stargazers_count", 0)
    meta = " · ".join(x for x in [lang, f"{stars} STAR" + ("" if stars == 1 else "S"), f"UPDATED {ago(repo.get('pushed_at'))}"] if x)
    rng = random.Random(repo["name"])
    dur, delay = 4.2 + rng.uniform(0, 1.6), rng.uniform(0, 3)

    css = font_face(700) + font_face(400) + f"""
.n{{font-family:'Orb700',Orbitron,'Segoe UI',sans-serif;font-size:{size}px;letter-spacing:3px;fill:#fff}}
.i{{font-family:'Orb700',Orbitron,monospace;font-size:14px;letter-spacing:3px;fill:#60a5fa}}
.d{{font-family:'Segoe UI',-apple-system,'Helvetica Neue',Arial,sans-serif;font-size:16px;fill:#c9d1d9}}
.m{{font-family:'Orb400',Orbitron,monospace;font-size:11px;letter-spacing:2px;fill:#60a5fa}}
.l{{font-family:'Orb400',Orbitron,monospace;font-size:13px;letter-spacing:3px;fill:#93c5fd}}
.edge{{stroke-dasharray:120 1500;animation:edge 4s linear infinite}}
@keyframes edge{{from{{stroke-dashoffset:1620}}to{{stroke-dashoffset:0}}}}
.f0{{opacity:0;animation:flash {dur:.2f}s {delay:.2f}s infinite steps(1,end)}}
@keyframes flash{{0%{{opacity:0}}86%{{opacity:1}}87.5%{{opacity:.15}}89%{{opacity:1}}92%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.edge{{animation:none;opacity:0}}.f0{{animation:none;opacity:.35}}}}"""

    p = bolt(470, 4, 520, 120, 26, rng)
    lines = wrap(desc, 58)
    body = f"""
<linearGradient id="cg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d1630"/><stop offset="1" stop-color="{BG}"/></linearGradient>
<rect x="4" y="4" width="{W-8}" height="{H-8}" rx="14" fill="url(#cg)" stroke="{B1}" stroke-width="1.5"/>
<rect class="edge" x="4" y="4" width="{W-8}" height="{H-8}" rx="14" stroke="{WHITE}" stroke-width="2.2" filter="url(#glow)"/>
<text class="i" x="32" y="46">// {idx:02d}</text>
<g class="f0" filter="url(#glow)"><path d="{p}" stroke="{B4}" stroke-width="2.2"/><path d="{p}" stroke="{WHITE}" stroke-width="1"/></g>
<path d="M548,26 L538,46 H547 L542,62 L558,40 H549 L553,26 Z" fill="{B2}" stroke="{B3}" stroke-width="1.2" filter="url(#glow)"/>
<text class="n" x="32" y="88" filter="url(#textglow)">{E(name)}</text>
""" + "\n".join(f'<text class="d" x="32" y="{122 + j*22}">{E(l)}</text>' for j, l in enumerate(lines)) + f"""
<text class="m" x="32" y="{H-30}">{E(meta)}</text>
<text class="l" x="{W-32}" y="{H-30}" text-anchor="end">VIEW REPO →</text>"""

    label = f"{repo['name']} — {desc}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{E(label)}" fill="none" stroke-linecap="round" stroke-linejoin="round">
<title>{E(label)}</title>
<style>{css}</style>
<defs>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="textglow" x="-20%" y="-50%" width="140%" height="200%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="6" result="b"/><feFlood flood-color="{B2}"/><feComposite in2="b" operator="in" result="g"/>
    <feGaussianBlur in="SourceAlpha" stdDeviation="2" result="b2"/><feFlood flood-color="{B3}"/><feComposite in2="b2" operator="in" result="g2"/>
    <feMerge><feMergeNode in="g"/><feMergeNode in="g"/><feMergeNode in="g2"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>{body}
</svg>
"""


# ---------------------------------------------------------------- README
def readme_block(repos):
    cells = []
    for i, r in enumerate(repos, 1):
        alt = E(f"{r['name']} — {r.get('description') or ''}".strip(" —"), quote=True)
        cells.append(f'    <td width="50%" align="center">\n'
                     f'      <a href="{r["html_url"]}"><img src="assets/cards/repo-{i}.svg" width="100%" alt="{alt}" /></a>\n'
                     f'    </td>')
    rows = ["  <tr>\n" + "\n".join(cells[i:i + 2]) + "\n  </tr>" for i in range(0, len(cells), 2)]
    return f"{START}\n<table>\n" + "\n".join(rows) + f"\n</table>\n{END}"


def main():
    if len(sys.argv) > 1:  # modo teste: JSON local no lugar da API
        repos = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        repos = starred_repos()
    chosen = pick(repos)
    if not chosen:
        print("Nenhum repositório elegível encontrado; README mantido.")
        return

    CARDS.mkdir(parents=True, exist_ok=True)
    for old in CARDS.glob("repo-*.svg"):
        old.unlink()
    for i, r in enumerate(chosen, 1):
        (CARDS / f"repo-{i}.svg").write_text(card(i, r), encoding="utf-8")

    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        sys.exit(f"Marcadores {START} / {END} não encontrados no README.md")
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: readme_block(chosen), text, flags=re.S)
    README.write_text(new, encoding="utf-8")
    print("Cards:", ", ".join(r["full_name"] for r in chosen))


if __name__ == "__main__":
    main()
