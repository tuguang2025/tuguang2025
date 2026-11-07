#!/usr/bin/env python3
import collections
import datetime
import html
import json
import os
import pathlib
import urllib.request

USER = os.environ.get("GITHUB_USER", "tuguang2025")
ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
TOKEN = os.environ.get("GITHUB_TOKEN")

THEMES = {
    "light": dict(bg="#ffffff", border="#d0d7de", fg="#1f2328", muted="#59636e", accent="#0969da", track="#eaeef2"),
    "dark": dict(bg="#0d1117", border="#30363d", fg="#e6edf3", muted="#9198a1", accent="#4493f8", track="#21262d"),
}

LANG_COLORS = {
    "Java": "#e76f00",
    "Python": "#3572a5",
    "Shell": "#89e051",
    "JavaScript": "#d9b514",
    "HTML": "#e34c26",
    "TypeScript": "#3178c6",
    "Solidity": "#aa6746",
    "Vue": "#41b883",
    "Go": "#00add8",
}


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-stats"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    req = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch():
    user = api("/users/" + USER)
    repos = []
    page = 1
    while True:
        batch = api("/users/%s/repos?per_page=100&type=owner&page=%d" % (USER, page))
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return user, repos


def esc(value):
    return html.escape(str(value))


def frame(width, height, theme, body):
    bg = theme["bg"]
    border = theme["border"]
    fg = theme["fg"]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img">\n'
        '<rect x="0.5" y="0.5" width="%d" height="%d" rx="8" fill="%s" stroke="%s"/>\n'
        '<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" fill="%s">\n'
        "%s\n</g>\n</svg>\n"
    ) % (width, height, width, height, width - 1, height - 1, bg, border, fg, body)


def stats_card(user, repos, theme):
    fg, muted, accent = theme["fg"], theme["muted"], theme["accent"]
    stars = sum(r["stargazers_count"] for r in repos)
    forks = sum(r["forks_count"] for r in repos)
    metrics = [
        ("Total stars", format(stars, ",")),
        ("Followers", format(user["followers"], ",")),
        ("Public repos", format(user["public_repos"], ",")),
        ("Total forks", format(forks, ",")),
        ("Following", format(user["following"], ",")),
        ("Joined", user["created_at"][:4]),
    ]
    updated = datetime.date.today().isoformat()
    parts = [
        "<text x=\"22\" y=\"30\" font-size=\"15\" font-weight=\"600\">%s's GitHub stats</text>" % esc(USER),
        '<text x="458" y="30" text-anchor="end" font-size="11" fill="%s">Updated %s</text>' % (muted, updated),
        '<line x1="22" y1="42" x2="458" y2="42" stroke="%s"/>' % theme["border"],
    ]
    for i, (label, value) in enumerate(metrics):
        x = 22 + (i % 2) * 230
        y = 68 + (i // 2) * 36
        parts.append('<text x="%d" y="%d" font-size="11" fill="%s">%s</text>' % (x, y, muted, label))
        parts.append('<text x="%d" y="%d" font-size="17" font-weight="600" fill="%s">%s</text>' % (x, y + 20, accent, value))
    parts.append('<text x="22" y="168" font-size="10" fill="%s" opacity="0.8">Static SVG generated from the GitHub API</text>' % muted)
    return frame(480, 180, theme, "\n".join(parts))


def langs_card(repos, theme):
    fg, muted = theme["fg"], theme["muted"]
    counts = collections.Counter(r["language"] for r in repos if r.get("language"))
    top = counts.most_common(5)
    labeled = sum(counts.values())
    parts = [
        '<text x="22" y="30" font-size="15" font-weight="600">Most used languages</text>',
        '<text x="458" y="30" text-anchor="end" font-size="11" fill="%s">%d repos with a primary language</text>' % (muted, labeled),
        '<line x1="22" y1="42" x2="458" y2="42" stroke="%s"/>' % theme["border"],
    ]
    for i, (lang, count) in enumerate(top):
        y = 60 + i * 27
        width = max(8, round(290 * count / top[0][1]))
        color = LANG_COLORS.get(lang, "#8250df")
        parts.append('<text x="22" y="%d" font-size="12" fill="%s">%s</text>' % (y + 12, fg, esc(lang)))
        parts.append('<rect x="130" y="%d" width="290" height="12" rx="6" fill="%s"/>' % (y + 2, theme["track"]))
        parts.append('<rect x="130" y="%d" width="%d" height="12" rx="6" fill="%s"/>' % (y + 2, width, color))
        parts.append('<text x="458" y="%d" text-anchor="end" font-size="11" fill="%s">%d</text>' % (y + 12, muted, count))
    parts.append('<text x="22" y="196" font-size="10" fill="%s" opacity="0.8">Counted by primary language, not lines of code</text>' % muted)
    return frame(480, 208, theme, "\n".join(parts))


def main():
    user, repos = fetch()
    if not ASSETS.is_dir():
        ASSETS.mkdir(parents=True)
    for name, theme in THEMES.items():
        suffix = "" if name == "light" else "-dark"
        (ASSETS / ("stats%s.svg" % suffix)).write_text(stats_card(user, repos, theme), encoding="utf-8")
        (ASSETS / ("langs%s.svg" % suffix)).write_text(langs_card(repos, theme), encoding="utf-8")
    print("updated stats cards for %s (%d repos)" % (USER, len(repos)))


if __name__ == "__main__":
    main()
