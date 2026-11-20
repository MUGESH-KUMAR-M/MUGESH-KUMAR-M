"""Build glass project cards: assets/cards/<id>-{dark,light}.svg from scripts/cards.json.

Tech icons are fetched from skillicons.dev and inlined, so the cards have no external
references (GitHub's image proxy blocks those inside SVGs).

    python scripts/build_cards.py
"""
import json
import re
import textwrap
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "cards"
W, H = 440, 210
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

THEMES = {
    "dark": dict(bg="#0D1117", glass="#161B22", border="#30363D", title="#E6EDF3",
                 text="#8B949E", kicker="#818CF8", c1="#6366F1", c2="#22D3EE", tint=0.14),
    "light": dict(bg="#FFFFFF", glass="#F6F8FA", border="#D0D7DE", title="#1F2328",
                  text="#57606A", kicker="#4F46E5", c1="#6366F1", c2="#06B6D4", tint=0.08),
}
_icon_cache = {}


def icon(name, theme):
    key = (name, theme)
    if key not in _icon_cache:
        url = f"https://skillicons.dev/icons?i={name}&theme={theme}"
        req = urllib.request.Request(url, headers={"User-Agent": "profile-card-builder"})
        svg = urllib.request.urlopen(req, timeout=30).read().decode()
        if 'width="48"' not in svg:
            raise SystemExit(f"skillicons has no icon '{name}'")
        # namespace ids so several icons can live in one document
        p = f"{name}-{theme}-"
        svg = re.sub(r'id="([^"]+)"', lambda m: f'id="{p}{m[1]}"', svg)
        svg = re.sub(r'url\(#([^)]+)\)', lambda m: f"url(#{p}{m[1]})", svg)
        svg = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{p}{m[1]}"', svg)
        _icon_cache[key] = svg
    return _icon_cache[key]


def place(svg, x, y, size):
    return re.sub(r"^\s*<svg ", f'<svg x="{x}" y="{y}" ', svg, count=1).replace(
        'width="48" height="48"', f'width="{size}" height="{size}"', 1)


def card(c, mode):
    t = THEMES[mode]
    status = c["status"]
    pill_w = 14 + 6.6 * len(status)
    lines = textwrap.wrap(c["outcome"], 54)[:3]
    outcome = "".join(
        f'<tspan x="24" dy="{0 if i == 0 else 20}">{escape(l)}</tspan>' for i, l in enumerate(lines))
    todo = "TODO" in c["outcome"]

    if c["icons"]:
        icons = "".join(place(icon(n, mode), 24 + i * 38, 160, 30) for i, n in enumerate(c["icons"]))
    else:
        icons = (f'<rect x="24" y="162" width="172" height="26" rx="13" fill="none" stroke="{t["border"]}" '
                 f'stroke-dasharray="4 4"/><text x="110" y="179.5" text-anchor="middle" font-size="11" font-family="{FONT}" '
                 f'fill="{t["text"]}">TODO: tech icons</text>')

    link = "View repo" if c["url"] else "Private repo"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(c['title'])}">
<title>{escape(c['title'])}</title>
<defs>
  <linearGradient id="tint" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{t['c1']}" stop-opacity="{t['tint']}"/>
    <stop offset="1" stop-color="{t['c2']}" stop-opacity="{t['tint'] / 2}"/>
  </linearGradient>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{t['c1']}"/><stop offset="1" stop-color="{t['c2']}"/>
  </linearGradient>
  <clipPath id="r"><rect width="{W}" height="{H}" rx="16"/></clipPath>
</defs>
<g clip-path="url(#r)">
  <rect width="{W}" height="{H}" fill="{t['glass']}"/>
  <rect width="{W}" height="{H}" fill="url(#tint)"/>
  <rect width="{W}" height="3" fill="url(#edge)"/>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="15.5" fill="none" stroke="{t['border']}"/>
<g font-family="{FONT}">
  <text x="24" y="38" font-size="11" font-weight="600" letter-spacing="1.4" fill="{t['kicker']}">{escape(c['kicker'])}</text>
  <rect x="{W - 24 - pill_w:.1f}" y="24" width="{pill_w:.1f}" height="22" rx="11" fill="none" stroke="{t['border']}"/>
  <text x="{W - 24 - pill_w / 2:.1f}" y="39" text-anchor="middle" font-size="11" fill="{t['text']}">{escape(status)}</text>
  <text x="24" y="70" font-size="22" font-weight="700" fill="{t['title']}">{escape(c['title'])}</text>
  <text x="24" y="98" font-size="13.5" fill="{t['text']}"{' font-style="italic"' if todo else ''}>{outcome}</text>
  <text x="{W - 24}" y="181" text-anchor="end" font-size="12.5" font-weight="600" fill="url(#edge)">{link}{' &#8594;' if c['url'] else ''}</text>
</g>
{icons}
</svg>
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cards = json.loads((ROOT / "scripts" / "cards.json").read_text(encoding="utf-8"))
    for c in cards:
        for mode in THEMES:
            (OUT / f"{c['id']}-{mode}.svg").write_text(card(c, mode), encoding="utf-8", newline="\n")
        print("built", c["id"])


if __name__ == "__main__":
    main()
