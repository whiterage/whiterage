#!/usr/bin/env python3
import os, math, requests, sys

USERNAME = os.getenv("GH_USERNAME") or os.getenv("GITHUB_ACTOR")
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
OUTPUT = os.getenv("OUTPUT_PATH", "assets/languages_donut_ios26_dark.svg")
TOP_N = int(os.getenv("TOP_N", "5"))
INCLUDE_PRIVATE = os.getenv("INCLUDE_PRIVATE", "false").lower() == "true"

if not USERNAME:
    print("✖ GH_USERNAME is required", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"token {TOKEN}"} if TOKEN else {}
API = "https://api.github.com"

def paged(url, params=None):
    items = []
    page = 1
    while True:
        p = params.copy() if params else {}
        p.update({"per_page": 100, "page": page})
        r = requests.get(url, headers=HEADERS, params=p, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        items.extend(data)
        if "next" not in r.links:
            break
        page += 1
    return items

def user_repos(username):
    return paged(f"{API}/users/{username}/repos", {"type": "owner", "sort": "updated"})

def repo_languages(owner, repo):
    r = requests.get(f"{API}/repos/{owner}/{repo}/languages", headers=HEADERS, timeout=30)
    if r.status_code == 204:
        return {}
    r.raise_for_status()
    return r.json()

def aggregate_langs(repos):
    total = {}
    for repo in repos:
        if repo.get("fork") or repo.get("archived"):
            continue
        langs = repo_languages(repo["owner"]["login"], repo["name"])
        for k,v in langs.items():
            total[k] = total.get(k, 0) + int(v)
    return total

def pick_palette():
    return {
        "background_top": "#0b1220",
        "background_bottom": "#0f172a",
        "label": "#EBE4D2",
        "legend_bg": "#ffffff14",
        "legend_text": "#E2E8F0",
        "colors": [
            "#38BDF8",
            "#6366F1",
            "#A855F7",
            "#10B981",
            "#14B8A6",
            "#F59E0B",
        ]
    }

def make_svg(data):
    pal = pick_palette()
    W,H = 1400, 560
    cx, cy = 420, 300
    r = 180
    stroke = 44

    total = sum(v for _,v in data) or 1
    data_sorted = sorted(data, key=lambda x: x[1], reverse=True)
    main = data_sorted[:TOP_N]
    other_sum = sum(v for _,v in data_sorted[TOP_N:])
    if other_sum > 0:
        main.append(("Other", other_sum))
    parts = [(name, v, v/total) for name,v in main]

    circumference = 2*math.pi*r
    gap = 0.01 * circumference

    offset = 0
    arcs = []
    colors = pal["colors"]
    for i,(name, _, pct) in enumerate(parts):
        seg = pct*circumference - gap
        if seg < 0:
            seg = 0
        color = colors[i] if i < len(colors) else colors[-1]
        arcs.append(f"""
        <circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='{color}' stroke-width='{stroke}'
                stroke-linecap='butt'
                stroke-dasharray='{seg:.3f} {circumference:.3f}'
                stroke-dashoffset='{-offset:.3f}' />""")
        offset += pct*circumference

    legend_x, legend_y = 760, 160
    legend_gap = 52
    legends = []
    for i,(name, v, pct) in enumerate(parts):
        color = colors[i] if i < len(colors) else colors[-1]
        pct_txt = f"{round(pct*100):d}%"
        legends.append(f"""
        <g transform='translate({legend_x},{legend_y + i*legend_gap})'>
          <rect x='0' y='-2' rx='20' ry='20' width='420' height='40' fill='{pal['legend_bg']}' />
          <circle cx='20' cy='18' r='10' fill='{color}' />
          <text x='46' y='24' font-size='20' font-family='Inter, ui-sans-serif, system-ui, -apple-system' fill='{pal['legend_text']}'>{name}</text>
          <text x='400' y='24' text-anchor='end' font-size='20' font-family='Inter, ui-sans-serif, system-ui, -apple-system' fill='{pal['label']}'>{pct_txt}</text>
        </g>
        """)

    svg = f"""<?xml version='1.0' encoding='UTF-8'?>
<svg width='{W}' height='{H}' viewBox='0 0 {W} {H}' fill='none' xmlns='http://www.w3.org/2000/svg'>
  <defs>
    <linearGradient id='bg' x1='0' y1='0' x2='0' y2='1'>
      <stop offset='0%' stop-color='{pal['background_top']}' />
      <stop offset='100%' stop-color='{pal['background_bottom']}' />
    </linearGradient>
    <filter id='blur' x='-20%' y='-20%' width='140%' height='140%'>
      <feGaussianBlur stdDeviation='60' />
    </filter>
  </defs>

  <rect width='100%' height='100%' fill='url(#bg)'/>
  <ellipse cx='{W*0.5}' cy='{H*0.9}' rx='{W*0.45}' ry='{H*0.4}' fill='#3B82F612' filter='url(#blur)'/>

  <circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='#0b1220' stroke-width='{stroke+2}' />

  {''.join(arcs)}

  <circle cx='{cx}' cy='{cy}' r='{r- stroke/2}' fill='url(#bg)'/>

  <text x='{cx}' y='{cy-10}' text-anchor='middle' font-size='22' font-family='Inter, ui-sans-serif, system-ui, -apple-system' fill='{pal['label']}' opacity='0.95'>Most Used</text>
  <text x='{cx}' y='{cy+22}' text-anchor='middle' font-size='22' font-family='Inter, ui-sans-serif, system-ui, -apple-system' fill='{pal['label']}' opacity='0.95'>Languages</text>

  {''.join(legends)}
</svg>
"""
    return svg

def main():
    repos = user_repos(USERNAME)
    langs = aggregate_langs(repos)
    if not langs:
        langs = {"Go": 1, "C++": 1}
    data = list(langs.items())
    svg = make_svg(data)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"✓ Wrote {OUTPUT}")

if __name__ == "__main__":
    main()
