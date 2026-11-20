"""Self-hosted GitHub stats cards in the profile palette (dark + light).

Writes <out>/{stats,langs,streak}-{dark,light}.svg using the GitHub GraphQL API.
Runs in CI with the built-in GITHUB_TOKEN (public data only), no third-party services.

    GITHUB_TOKEN=... python scripts/stats.py --user MUGESH-KUMAR-M --out dist
"""
import argparse
import datetime as dt
import json
import os
import urllib.request
from html import escape
from pathlib import Path

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
THEMES = {
    "dark": dict(glass="#161B22", border="#30363D", title="#E6EDF3", text="#8B949E",
                 track="#21262D", c1="#6366F1", c2="#22D3EE", tint=0.14),
    "light": dict(glass="#F6F8FA", border="#D0D7DE", title="#1F2328", text="#57606A",
                  track="#E5E7EB", c1="#6366F1", c2="#06B6D4", tint=0.08),
}
# indigo -> cyan ramp for language segments
RAMP = ["#6366F1", "#5B7BF0", "#4F93EE", "#3FAAEA", "#30BFE6", "#22D3EE", "#8B949E"]

QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
    }
  }
}"""


def gql(token, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-stats"})
    data = json.load(urllib.request.urlopen(req, timeout=60))
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]


def fetch(login, token):
    user, repos, cursor = None, [], None
    while True:
        page = gql(token, {"login": login, "cursor": cursor})
        user = user or page
        repos += page["repositories"]["nodes"]
        info = page["repositories"]["pageInfo"]
        if not info["hasNextPage"]:
            break
        cursor = info["endCursor"]
    return user, repos


def streaks(days):
    days = sorted(days, key=lambda d: d["date"])
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    current = 0
    tail = days[:-1] if days and not days[-1]["contributionCount"] else days  # today may be empty
    for d in reversed(tail):
        if not d["contributionCount"]:
            break
        current += 1
    return current, longest


def frame(w, h, t, title, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{escape(title)}">
<title>{escape(title)}</title>
<defs>
  <linearGradient id="tint" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{t['c1']}" stop-opacity="{t['tint']}"/><stop offset="1" stop-color="{t['c2']}" stop-opacity="{t['tint'] / 2}"/>
  </linearGradient>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t['c1']}"/><stop offset="1" stop-color="{t['c2']}"/></linearGradient>
  <clipPath id="r"><rect width="{w}" height="{h}" rx="16"/></clipPath>
</defs>
<g clip-path="url(#r)"><rect width="{w}" height="{h}" fill="{t['glass']}"/><rect width="{w}" height="{h}" fill="url(#tint)"/><rect width="{w}" height="3" fill="url(#edge)"/></g>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="15.5" fill="none" stroke="{t['border']}"/>
<g font-family="{FONT}">
<text x="24" y="40" font-size="16" font-weight="700" fill="{t['title']}">{escape(title)}</text>
{body}
</g>
</svg>
"""


def stats_card(s, t):
    rows = [("Total stars", s["stars"]), ("Contributions (last year)", s["contrib"]),
            ("Commits (last year)", s["commits"]), ("Pull requests", s["prs"]),
            ("Issues", s["issues"]), ("Public repos", s["repos"])]
    body = "".join(
        f'<text x="24" y="{76 + i * 22}" font-size="13" fill="{t["text"]}">{k}</text>'
        f'<text x="416" y="{76 + i * 22}" font-size="13" font-weight="700" text-anchor="end" fill="{t["title"]}">{v:,}</text>'
        for i, (k, v) in enumerate(rows))
    return frame(440, 210, t, "GitHub Stats", body)


def langs_card(langs, t):
    total = sum(v for _, v in langs) or 1
    top = langs[:6]
    rest = total - sum(v for _, v in top)
    if rest > 0:
        top.append(("Other", rest))
    x, bar = 24.0, ""
    for i, (name, v) in enumerate(top):
        w = 392 * v / total
        bar += f'<rect x="{x:.2f}" y="58" width="{w:.2f}" height="10" fill="{RAMP[i]}"/>'
        x += w
    bar = (f'<clipPath id="bar"><rect x="24" y="58" width="392" height="10" rx="5"/></clipPath>'
           f'<rect x="24" y="58" width="392" height="10" rx="5" fill="{t["track"]}"/><g clip-path="url(#bar)">{bar}</g>')
    legend = ""
    for i, (name, v) in enumerate(top):
        cx, cy = 24 + (i % 2) * 200, 100 + (i // 2) * 26
        legend += (f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{RAMP[i]}"/>'
                   f'<text x="{cx + 16}" y="{cy}" font-size="13" fill="{t["title"]}">{escape(name)}'
                   f'<tspan fill="{t["text"]}"> {100 * v / total:.1f}%</tspan></text>')
    return frame(440, 210, t, "Top Languages", bar + legend)


def days(n):
    return f"{n} day" if n == 1 else f"{n} days"


def streak_card(s, t):
    cols = [("Total contributions", f'{s["contrib"]:,}', "last 12 months"),
            ("Current streak", days(s["current"]), "consecutive"),
            ("Longest streak", days(s["longest"]), "last 12 months")]
    body = ""
    for i, (label, value, sub) in enumerate(cols):
        cx = 150 + i * 300
        fill = "url(#edge)" if i == 1 else t["title"]
        body += (f'<text x="{cx}" y="92" text-anchor="middle" font-size="30" font-weight="800" fill="{fill}">{value}</text>'
                 f'<text x="{cx}" y="120" text-anchor="middle" font-size="13" font-weight="600" fill="{t["title"]}">{label}</text>'
                 f'<text x="{cx}" y="140" text-anchor="middle" font-size="11.5" fill="{t["text"]}">{sub}</text>')
        if i:
            body += f'<rect x="{cx - 150}" y="62" width="1" height="82" fill="{t["border"]}"/>'
    return frame(900, 170, t, "Contribution Streak", body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--out", default="dist")
    ap.add_argument("--sample", action="store_true", help="render with sample numbers (no API)")
    a = ap.parse_args()

    if a.sample:
        days = [{"date": f"2026-01-{d:02d}", "contributionCount": d % 4} for d in range(1, 29)]
        user = {"followers": {"totalCount": 0}, "pullRequests": {"totalCount": 12}, "issues": {"totalCount": 4},
                "contributionsCollection": {"totalCommitContributions": 420, "contributionCalendar": {
                    "totalContributions": 512, "weeks": [{"contributionDays": days}]}}}
        repos = [{"stargazerCount": 3, "languages": {"edges": [
            {"size": s, "node": {"name": n}} for n, s in
            [("Python", 900), ("TypeScript", 500), ("JavaScript", 300), ("HTML", 90), ("CSS", 60), ("Jupyter Notebook", 40), ("Shell", 10)]]}}] * 5
    else:
        user, repos = fetch(a.user, os.environ["GITHUB_TOKEN"])

    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    cc = user["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    current, longest = streaks(days)
    s = dict(stars=sum(r["stargazerCount"] for r in repos), contrib=cc["contributionCalendar"]["totalContributions"],
             commits=cc["totalCommitContributions"], prs=user["pullRequests"]["totalCount"],
             issues=user["issues"]["totalCount"], repos=len(repos), current=current, longest=longest)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ranked = sorted(langs.items(), key=lambda kv: -kv[1])
    for mode, t in THEMES.items():
        (out / f"stats-{mode}.svg").write_text(stats_card(s, t), encoding="utf-8")
        (out / f"langs-{mode}.svg").write_text(langs_card(list(ranked), t), encoding="utf-8")
        (out / f"streak-{mode}.svg").write_text(streak_card(s, t), encoding="utf-8")
    print(json.dumps(s))


if __name__ == "__main__":
    main()
