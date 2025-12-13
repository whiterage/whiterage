#!/usr/bin/env python3
"""
Generate language statistics SVG for GitHub profile
Hardcoded for whiterage profile
"""
import os
import math
import requests
import sys

# Hardcoded for whiterage profile
GITHUB_USERNAME = "whiterage"
OUTPUT_FILE = "assets/languages_donut.svg"
TOP_N_LANGUAGES = 5

# GitHub API setup
GITHUB_TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
API_BASE = "https://api.github.com"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def fetch_all_pages(url, params=None):
    """Fetch all pages from GitHub API"""
    items = []
    page = 1
    while True:
        page_params = params.copy() if params else {}
        page_params.update({"per_page": 100, "page": page})

        try:
            response = requests.get(
                url, headers=HEADERS, params=page_params, timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if not data:
                break

            items.extend(data)

            # Check if there's a next page
            if "next" not in response.links:
                break

            page += 1
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching data: {e}", file=sys.stderr)
            sys.exit(1)

    return items


def get_user_repositories(username):
    """Get all repositories for a user"""
    url = f"{API_BASE}/users/{username}/repos"
    params = {"type": "owner", "sort": "updated"}
    return fetch_all_pages(url, params)


def get_repo_languages(owner, repo):
    """Get language statistics for a repository"""
    url = f"{API_BASE}/repos/{owner}/{repo}/languages"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)

        if response.status_code == 204:
            return {}

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {}


def aggregate_languages(repos):
    """Aggregate language statistics from all repositories"""
    total_languages = {}

    for repo in repos:
        # Skip forks and archived repos
        if repo.get("fork") or repo.get("archived"):
            continue

        owner = repo["owner"]["login"]
        repo_name = repo["name"]

        languages = get_repo_languages(owner, repo_name)

        for lang, bytes_count in languages.items():
            total_languages[lang] = total_languages.get(lang, 0) + int(bytes_count)

    return total_languages


def generate_svg(language_data):
    """Generate SVG chart from language data"""
    # Color palette matching your theme
    colors = [
        "#6366F1",  # Indigo (your main color)
        "#A855F7",  # Purple
        "#38BDF8",  # Sky blue
        "#10B981",  # Green
        "#14B8A6",  # Teal
        "#F59E0B",  # Amber
    ]

    # SVG dimensions
    width, height = 1400, 560
    center_x, center_y = 420, 300
    radius = 180
    stroke_width = 44

    # Process data
    total_bytes = sum(v for _, v in language_data) or 1
    sorted_data = sorted(language_data, key=lambda x: x[1], reverse=True)

    # Get top N languages
    top_languages = sorted_data[:TOP_N_LANGUAGES]
    other_bytes = sum(v for _, v in sorted_data[TOP_N_LANGUAGES:])

    if other_bytes > 0:
        top_languages.append(("Other", other_bytes))

    # Calculate percentages
    segments = [
        (name, bytes_count, bytes_count / total_bytes)
        for name, bytes_count in top_languages
    ]

    # Generate donut chart arcs
    circumference = 2 * math.pi * radius
    gap = 0.01 * circumference

    arcs = []
    offset = 0

    for i, (name, _, percentage) in enumerate(segments):
        segment_length = percentage * circumference - gap
        if segment_length < 0:
            segment_length = 0

        color = colors[i % len(colors)]

        arcs.append(
            f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" '
            f'fill="none" stroke="{color}" stroke-width="{stroke_width}" '
            f'stroke-linecap="butt" '
            f'stroke-dasharray="{segment_length:.3f} {circumference:.3f}" '
            f'stroke-dashoffset="{-offset:.3f}" />'
        )

        offset += percentage * circumference

    # Generate legend
    legend_x, legend_y = 760, 160
    legend_gap = 52
    legends = []

    for i, (name, _, percentage) in enumerate(segments):
        color = colors[i % len(colors)]
        percentage_text = f"{round(percentage * 100)}%"

        legends.append(
            f'<g transform="translate({legend_x},{legend_y + i * legend_gap})">'
            f'<rect x="0" y="-2" rx="20" ry="20" width="420" height="40" '
            f'fill="#ffffff14" />'
            f'<circle cx="20" cy="18" r="10" fill="{color}" />'
            f'<text x="46" y="24" font-size="20" '
            f'font-family="Inter, ui-sans-serif, system-ui, -apple-system" '
            f'fill="#E2E8F0">{name}</text>'
            f'<text x="400" y="24" text-anchor="end" font-size="20" '
            f'font-family="Inter, ui-sans-serif, system-ui, -apple-system" '
            f'fill="#EBE4D2">{percentage_text}</text>'
            f"</g>"
        )

    # Build complete SVG
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0b1220" />
      <stop offset="100%" stop-color="#0f172a" />
    </linearGradient>
    <filter id="blur" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="60" />
    </filter>
  </defs>

  <rect width="100%" height="100%" fill="url(#bg)"/>
  <ellipse cx="{width * 0.5}" cy="{height * 0.9}" rx="{width * 0.45}" ry="{height * 0.4}" fill="#3B82F612" filter="url(#blur)"/>

  <circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="none" stroke="#0b1220" stroke-width="{stroke_width + 2}" />

  {''.join(arcs)}

  <circle cx="{center_x}" cy="{center_y}" r="{radius - stroke_width / 2}" fill="url(#bg)"/>

  <text x="{center_x}" y="{center_y - 10}" text-anchor="middle" font-size="22" font-family="Inter, ui-sans-serif, system-ui, -apple-system" fill="#EBE4D2" opacity="0.95">Most Used</text>
  <text x="{center_x}" y="{center_y + 22}" text-anchor="middle" font-size="22" font-family="Inter, ui-sans-serif, system-ui, -apple-system" fill="#EBE4D2" opacity="0.95">Languages</text>

  {''.join(legends)}
</svg>"""

    return svg


def main():
    """Main function"""
    print(f"🔍 Fetching repositories for: {GITHUB_USERNAME}")

    # Get all repositories
    repos = get_user_repositories(GITHUB_USERNAME)
    print(f"📦 Found {len(repos)} repositories")

    if not repos:
        print("⚠️  No repositories found!", file=sys.stderr)
        sys.exit(1)

    # Aggregate languages
    print("📊 Analyzing languages...")
    languages = aggregate_languages(repos)

    if not languages:
        print("⚠️  No language data found!", file=sys.stderr)
        sys.exit(1)

    # Convert to list and show top languages
    language_list = list(languages.items())
    top_langs = sorted(language_list, key=lambda x: x[1], reverse=True)[:5]
    print(
        f"✅ Top languages: {', '.join([f'{name} ({bytes_count:,} bytes)' for name, bytes_count in top_langs])}"
    )

    # Generate SVG
    print("🎨 Generating SVG...")
    svg_content = generate_svg(language_list)

    # Write to file
    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(svg_content)

    print(f"✅ Successfully created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
