#!/usr/bin/env python3
import os, math, requests, sys

USERNAME = os.getenv("GH_USERNAME") or os.getenv("GITHUB_ACTOR")
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
OUTPUT = os.getenv("OUTPUT_PATH", "assets/languages_donut.svg")
TOP_N = int(os.getenv("TOP_N", "6"))
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
    """Современная палитра с градиентами и неоновыми акцентами"""
    return {
        "background_top": "#0D1117",
        "background_bottom": "#161B22",
        "center_gradient_start": "#1a1f2e",
        "center_gradient_end": "#0D1117",
        "label": "#E6EDF3",
        "subtitle": "#8B949E",
        "legend_bg": "#21262D",
        "legend_border": "#30363D",
        "legend_text": "#E6EDF3",
        "legend_percentage": "#A177FF",
        "glow_color": "#A177FF",
        "colors": [
            "#A177FF",  # Purple
            "#3B82F6",  # Blue
            "#10B981",  # Green
            "#F59E0B",  # Orange
            "#EF4444",  # Red
            "#EC4899",  # Pink
            "#8B5CF6",  # Violet
            "#14B8A6",  # Teal
        ]
    }

def make_svg(data):
    pal = pick_palette()
    W, H = 1600, 600
    cx, cy = 450, 300
    r = 200
    stroke = 50

    total = sum(v for _, v in data) or 1
    data_sorted = sorted(data, key=lambda x: x[1], reverse=True)
    main = data_sorted[:TOP_N]
    other_sum = sum(v for _, v in data_sorted[TOP_N:])
    if other_sum > 0:
        main.append(("Other", other_sum))
    parts = [(name, v, v/total) for name, v in main]

    circumference = 2 * math.pi * r
    gap = 0.005 * circumference  # Меньший зазор для более плотного вида

    offset = 0
    arcs = []
    glow_arcs = []
    colors = pal["colors"]
    
    for i, (name, _, pct) in enumerate(parts):
        seg = pct * circumference - gap
        if seg < 0:
            seg = 0
        color = colors[i % len(colors)]
        
        # Основная дуга
        arcs.append(f"""
        <circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='{color}' stroke-width='{stroke}'
                stroke-linecap='round'
                stroke-dasharray='{seg:.3f} {circumference:.3f}'
                stroke-dashoffset='{-offset:.3f}'
                opacity='0.9' />""")
        
        # Эффект свечения (для топ языка)
        if i == 0:
            glow_arcs.append(f"""
            <circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='{color}' stroke-width='{stroke + 4}'
                    stroke-linecap='round'
                    stroke-dasharray='{seg:.3f} {circumference:.3f}'
                    stroke-dashoffset='{-offset:.3f}'
                    opacity='0.3' filter='url(#glow)' />""")
        
        offset += pct * circumference

    # Легенда с улучшенным дизайном
    legend_x, legend_y = 820, 100
    legend_gap = 62
    legends = []
    
    for i, (name, v, pct) in enumerate(parts):
        color = colors[i % len(colors)]
        pct_txt = f"{round(pct*100, 1)}%"
        
        # Подсчет размера в KB/MB
        size = v / 1024  # KB
        if size > 1024:
            size_txt = f"{size/1024:.1f} MB"
        else:
            size_txt = f"{size:.0f} KB"
        
        y = legend_y + i * legend_gap
        
        legends.append(f"""
        <g transform='translate({legend_x},{y})' class='legend-item'>
          <!-- Фон карточки с тенью -->
          <rect x='0' y='0' rx='12' ry='12' width='520' height='52' 
                fill='{pal['legend_bg']}' 
                stroke='{pal['legend_border']}' 
                stroke-width='1.5'
                filter='url(#shadow)' />
          
          <!-- Индикатор цвета -->
          <rect x='16' y='16' rx='6' ry='6' width='20' height='20' fill='{color}' />
          
          <!-- Название языка -->
          <text x='50' y='32' font-size='18' font-weight='600' 
                font-family='Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif' 
                fill='{pal['legend_text']}'>{name}</text>
          
          <!-- Размер -->
          <text x='280' y='32' font-size='14' font-weight='400' 
                font-family='Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif' 
                fill='{pal['subtitle']}' opacity='0.8'>{size_txt}</text>
          
          <!-- Процент -->
          <text x='495' y='32' text-anchor='end' font-size='20' font-weight='700' 
                font-family='Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif' 
                fill='{pal['legend_percentage']}'>{pct_txt}</text>
          
          <!-- Прогресс бар -->
          <rect x='16' y='42' rx='2' ry='2' width='488' height='3' 
                fill='{pal['legend_border']}' opacity='0.3' />
          <rect x='16' y='42' rx='2' ry='2' width='{488 * pct}' height='3' 
                fill='{color}' opacity='0.8' />
        </g>
        """)

    # Декоративные элементы
    decorations = f"""
    <!-- Декоративные круги на фоне -->
    <circle cx='180' cy='100' r='120' fill='#3B82F6' opacity='0.03' filter='url(#blur)' />
    <circle cx='{W-180}' cy='{H-100}' r='150' fill='#A177FF' opacity='0.04' filter='url(#blur)' />
    <circle cx='200' cy='{H-80}' r='100' fill='#10B981' opacity='0.03' filter='url(#blur)' />
    
    <!-- Линии декора -->
    <line x1='720' y1='60' x2='1380' y2='60' stroke='{pal['legend_border']}' stroke-width='2' opacity='0.3' />
    <line x1='720' y1='{H-60}' x2='1380' y2='{H-60}' stroke='{pal['legend_border']}' stroke-width='2' opacity='0.3' />
    """

    svg = f"""<?xml version='1.0' encoding='UTF-8'?>
<svg width='{W}' height='{H}' viewBox='0 0 {W} {H}' fill='none' xmlns='http://www.w3.org/2000/svg'>
  <defs>
    <!-- Градиенты -->
    <linearGradient id='bg' x1='0' y1='0' x2='0' y2='1'>
      <stop offset='0%' stop-color='{pal['background_top']}' />
      <stop offset='100%' stop-color='{pal['background_bottom']}' />
    </linearGradient>
    
    <radialGradient id='centerGradient' cx='50%' cy='50%'>
      <stop offset='0%' stop-color='{pal['center_gradient_start']}' />
      <stop offset='100%' stop-color='{pal['center_gradient_end']}' />
    </radialGradient>
    
    <!-- Фильтры -->
    <filter id='blur' x='-50%' y='-50%' width='200%' height='200%'>
      <feGaussianBlur stdDeviation='80' />
    </filter>
    
    <filter id='glow' x='-50%' y='-50%' width='200%' height='200%'>
      <feGaussianBlur stdDeviation='8' />
    </filter>
    
    <filter id='shadow' x='-20%' y='-20%' width='140%' height='140%'>
      <feGaussianBlur in='SourceAlpha' stdDeviation='3'/>
      <feOffset dx='0' dy='2' result='offsetblur'/>
      <feComponentTransfer>
        <feFuncA type='linear' slope='0.2'/>
      </feComponentTransfer>
      <feMerge>
        <feMergeNode/>
        <feMergeNode in='SourceGraphic'/>
      </feMerge>
    </filter>
  </defs>

  <!-- Фон -->
  <rect width='100%' height='100%' fill='url(#bg)'/>
  
  {decorations}

  <!-- Внешнее кольцо с тенью -->
  <circle cx='{cx}' cy='{cy}' r='{r + stroke/2 + 8}' fill='none' 
          stroke='{pal['legend_border']}' stroke-width='2' opacity='0.15' />

  <!-- Эффекты свечения -->
  {''.join(glow_arcs)}

  <!-- Основные дуги -->
  {''.join(arcs)}

  <!-- Внутренний круг с градиентом -->
  <circle cx='{cx}' cy='{cy}' r='{r - stroke/2 - 2}' fill='url(#centerGradient)' 
          stroke='{pal['legend_border']}' stroke-width='2' opacity='0.5' />

  <!-- Текст в центре -->
  <g transform='translate({cx},{cy})'>
    <text x='0' y='-35' text-anchor='middle' font-size='18' font-weight='500'
          font-family='Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif' 
          fill='{pal['subtitle']}' opacity='0.8'>
      💻 MOST USED
    </text>
    <text x='0' y='5' text-anchor='middle' font-size='32' font-weight='700'
          font-family='Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif' 
          fill='{pal['label']}'>
      Languages
    </text>
    <text x='0' y='35' text-anchor='middle' font-size='16' font-weight='400'
          font-family='Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif' 
          fill='{pal['subtitle']}' opacity='0.6'>
      {len(data)} languages tracked
    </text>
  </g>

  <!-- Заголовок легенды -->
  <text x='{legend_x + 20}' y='70' font-size='20' font-weight='700'
        font-family='Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif' 
        fill='{pal['label']}'>
    📊 Statistics
  </text>

  <!-- Легенда -->
  {''.join(legends)}

  <!-- Подпись -->
  <text x='{W/2}' y='{H-20}' text-anchor='middle' font-size='13' 
        font-family='Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif' 
        fill='{pal['subtitle']}' opacity='0.5'>
    Generated with ❤️ by GitHub Language Stats
  </text>
</svg>
"""
    return svg

def main():
    print("🔍 Fetching repositories...")
    repos = user_repos(USERNAME)
    print(f"✓ Found {len(repos)} repositories")
    
    print("📊 Analyzing languages...")
    langs = aggregate_langs(repos)
    
    if not langs:
        print("⚠ No languages found, using defaults")
        langs = {"Python": 1000, "Go": 800, "JavaScript": 600}
    
    data = list(langs.items())
    print(f"✓ Analyzed {len(data)} languages")
    
    print("🎨 Generating SVG...")
    svg = make_svg(data)
    
    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(svg)
    
    print(f"✅ Successfully created: {OUTPUT}")
    print(f"📈 Top languages: {', '.join([name for name, _ in sorted(data, key=lambda x: x[1], reverse=True)[:5]])}")

if __name__ == "__main__":
    main()
