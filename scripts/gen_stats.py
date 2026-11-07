#!/usr/bin/env python3
import collections
import concurrent.futures
import datetime
import html
import json
import os
import pathlib
import subprocess
import urllib.request

USER = os.environ.get("GITHUB_USER", "tuguang2025")
ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
TOP_N = 8

THEMES = {
    "light": dict(bg="#ffffff", border="#d0d7de", fg="#1f2328", muted="#59636e", accent="#0969da", track="#eaeef2"),
    "dark": dict(bg="#0d1117", border="#30363d", fg="#e6edf3", muted="#9198a1", accent="#4493f8", track="#21262d"),
}

LANG_COLORS = {
    "JavaScript": "#e5c73b",
    "Java": "#b07219",
    "HTML": "#e34c26",
    "TypeScript": "#3178c6",
    "Vue": "#41b883",
    "CSS": "#663399",
    "Python": "#3572a5",
    "Shell": "#89e051",
    "SCSS": "#c6538c",
    "Solidity": "#aa6746",
    "Dockerfile": "#384d54",
    "Lua": "#3f5cbf",
    "C": "#8a8a8a",
    "C++": "#f34b7d",
    "C#": "#178600",
    "Go": "#00add8",
    "Swift": "#f05138",
    "Kotlin": "#a97bff",
    "PHP": "#4f5d95",
    "Ruby": "#e05a70",
    "Rust": "#dea584",
    "Dart": "#00b4ab",
    "Jupyter Notebook": "#da5b0b",
    "Gherkin": "#8f5ba8",
    "Move": "#7b68ee",
    "Less": "#5a7fb5",
    "Roff": "#b09070",
}


def resolve_token():
    value = os.environ.get("GITHUB_TOKEN")
    if value:
        return value
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


TOKEN = resolve_token()


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-stats"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    req = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def repo_languages(repo):
    try:
        return api("/repos/%s/%s/languages" % (USER, repo["name"]))
    except Exception:
        return {}


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
    own = [r for r in repos if not r["fork"]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        per_repo = list(pool.map(repo_languages, own))
    totals = collections.Counter()
    with_code = 0
    for data in per_repo:
        if data:
            with_code += 1
        totals.update(data)
    return user, repos, totals, len(own), with_code


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


def langs_card(totals, own_count, with_code, theme):
    fg, muted = theme["fg"], theme["muted"]
    top = totals.most_common(TOP_N)
    total_bytes = sum(totals.values())
    parts = [
        '<text x="22" y="30" font-size="15" font-weight="600">Most used languages</text>',
        '<text x="458" y="30" text-anchor="end" font-size="11" fill="%s">%d own repos with code · %.1f MB</text>'
        % (muted, with_code, total_bytes / 1048576),
        '<line x1="22" y1="42" x2="458" y2="42" stroke="%s"/>' % theme["border"],
    ]
    for i, (lang, size) in enumerate(top):
        y = 56 + i * 26
        width = max(4, round(250 * size / top[0][1]))
        color = LANG_COLORS.get(lang, "#8250df")
        parts.append('<text x="22" y="%d" font-size="12" fill="%s">%s</text>' % (y + 12, fg, esc(lang)))
        parts.append('<rect x="140" y="%d" width="250" height="12" rx="6" fill="%s"/>' % (y + 2, theme["track"]))
        parts.append('<rect x="140" y="%d" width="%d" height="12" rx="6" fill="%s"/>' % (y + 2, width, color))
        parts.append('<text x="458" y="%d" text-anchor="end" font-size="11" fill="%s">%.1f%%</text>'
                     % (y + 12, muted, 100.0 * size / total_bytes))
    footer = "%d languages detected · top %d shown · forks excluded · GitHub Linguist byte share" % (len(totals), len(top))
    parts.append('<text x="22" y="274" font-size="10" fill="%s" opacity="0.8">%s</text>' % (muted, esc(footer)))
    return frame(480, 288, theme, "\n".join(parts))


def main():
    user, repos, totals, own_count, with_code = fetch()
    if not ASSETS.is_dir():
        ASSETS.mkdir(parents=True)
    for name, theme in THEMES.items():
        suffix = "" if name == "light" else "-dark"
        (ASSETS / ("stats%s.svg" % suffix)).write_text(stats_card(user, repos, theme), encoding="utf-8")
        (ASSETS / ("langs%s.svg" % suffix)).write_text(langs_card(totals, own_count, with_code, theme), encoding="utf-8")
    print("updated cards for %s (%d own repos, %d languages)" % (USER, own_count, len(totals)))


if __name__ == "__main__":
    main()
