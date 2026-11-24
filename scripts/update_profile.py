#!/usr/bin/env python3
"""Render light and dark GitHub activity SVGs using only Python's standard library."""

import argparse
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

QUERY = """
query ProfileActivity($login: String!) {
  user(login: $login) {
    login
    followers { totalCount }
    repositories(privacy: PUBLIC, ownerAffiliations: [OWNER]) { totalCount }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date weekday contributionCount contributionLevel }
        }
      }
    }
  }
}
"""

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "rule": "#21262d",
        "text": "#e6edf3",
        "sub": "#8b949e",
        "muted": "#6e7681",
        "cell_stroke": "#1b2028",
        "levels": {
            "NONE": "#161b22",
            "FIRST_QUARTILE": "#0e4429",
            "SECOND_QUARTILE": "#006d32",
            "THIRD_QUARTILE": "#26a641",
            "FOURTH_QUARTILE": "#39d353",
        },
        "overlay_bg": "#161b22",
        "overlay_border": "#30363d",
    },
    "light": {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "rule": "#e5e9ee",
        "text": "#1f2328",
        "sub": "#59636e",
        "muted": "#6e7781",
        "cell_stroke": "#d8dee4",
        "levels": {
            "NONE": "#ebedf0",
            "FIRST_QUARTILE": "#9be9a8",
            "SECOND_QUARTILE": "#40c463",
            "THIRD_QUARTILE": "#30a14e",
            "FOURTH_QUARTILE": "#216e39",
        },
        "overlay_bg": "#f6f8fa",
        "overlay_border": "#d0d7de",
    },
}

VALID_LEVELS = set(THEMES["dark"]["levels"].keys())


def fetch_profile(username, token):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": username}}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "shakil42051-profile-activity",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def validate_profile(payload, username):
    if payload.get("errors"):
        raise ValueError("GitHub returned a GraphQL error; existing cards were preserved.")
    profile = payload.get("data", {}).get("user")
    if not profile or profile.get("login", "").lower() != username.lower():
        raise ValueError("No matching GitHub user was returned; existing cards were preserved.")
    calendar = profile["contributionsCollection"]["contributionCalendar"]
    if not 1 <= len(calendar["weeks"]) <= 54:
        raise ValueError("Unexpected contribution calendar length.")
    counts = [
        calendar["totalContributions"],
        profile["followers"]["totalCount"],
        profile["repositories"]["totalCount"],
    ]
    dates = set()
    for week in calendar["weeks"]:
        if len(week["contributionDays"]) > 7:
            raise ValueError("Unexpected number of days in a week.")
        for day in week["contributionDays"]:
            parsed = dt.date.fromisoformat(day["date"])
            if day["date"] in dates or day["weekday"] != (parsed.weekday() + 1) % 7:
                raise ValueError("Invalid or repeated contribution date.")
            dates.add(day["date"])
            if day["contributionLevel"] not in VALID_LEVELS:
                raise ValueError("Unknown contribution level.")
            counts.append(day["contributionCount"])
    if not all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in counts):
        raise ValueError("Invalid activity counts.")
    if not dates:
        raise ValueError("GitHub returned an empty calendar.")
    return profile


def longest_streak(weeks):
    all_days = sorted(
        (day for week in weeks for day in week["contributionDays"]),
        key=lambda day: day["date"],
    )
    best = current = 0
    for day in all_days:
        if day["contributionCount"] > 0:
            current += 1
            if current > best:
                best = current
        else:
            current = 0
    return best


def render_card(profile, username, sync_date, theme_name):
    palette = THEMES[theme_name]
    levels = palette["levels"]
    placeholder = profile is None
    escaped_name = html.escape(username)
    sans = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    mono = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

    if placeholder:
        metrics = [
            ("—", "Contributions (1y)"),
            ("—", "Active days"),
            ("—", "Public repositories"),
            ("—", "Longest streak"),
        ]
        last_sunday = dt.date(2026, 1, 4)
        weeks = [
            {
                "contributionDays": [
                    {
                        "date": (last_sunday + dt.timedelta(days=7 * week + day)).isoformat(),
                        "weekday": day,
                        "contributionCount": 0,
                        "contributionLevel": "NONE",
                    }
                    for day in range(7)
                ]
            }
            for week in range(53)
        ]
    else:
        calendar = profile["contributionsCollection"]["contributionCalendar"]
        weeks = calendar["weeks"]
        active = sum(
            day["contributionCount"] > 0
            for week in weeks
            for day in week["contributionDays"]
        )
        streak = longest_streak(weeks)
        streak_label = f"{streak} {'day' if streak == 1 else 'days'}"
        metrics = [
            (f'{calendar["totalContributions"]:,}', "Contributions (past year)"),
            (f"{active:,}", "Active days"),
            (f'{profile["repositories"]["totalCount"]:,}', "Public repositories"),
            (streak_label, "Longest streak"),
        ]

    desc = (
        "Awaiting first sync. Run the included GitHub Actions workflow to load real data."
        if placeholder
        else f"GitHub contribution calendar and public stats for @{escaped_name}. Synced {sync_date} UTC."
    )

    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="270" viewBox="0 0 900 270" role="img" aria-labelledby="title desc">',
        f'<title id="title">GitHub activity for @{escaped_name}</title>',
        f'<desc id="desc">{desc}</desc>',
        f'<rect x="0.5" y="0.5" width="899" height="269" rx="12" fill="{palette["bg"]}" stroke="{palette["border"]}"/>',
        f'<g font-family="{sans}">',
        f'  <text x="32" y="34" fill="{palette["text"]}" font-size="13" font-weight="600">Contribution activity</text>',
        f'  <text x="868" y="34" text-anchor="end" fill="{palette["muted"]}" font-family="{mono}" font-size="11">@{escaped_name}</text>',
    ]

    for x, (value, label) in zip([32, 248, 464, 680], metrics):
        elements.append(
            f'  <text x="{x}" y="70" fill="{palette["text"]}" font-size="23" font-weight="700" letter-spacing="-0.4">{html.escape(value)}</text>'
        )
        elements.append(
            f'  <text x="{x}" y="88" fill="{palette["sub"]}" font-size="11">{html.escape(label)}</text>'
        )

    elements.append(f'  <line x1="32" y1="104" x2="868" y2="104" stroke="{palette["rule"]}" stroke-width="1"/>')

    grid_x = 76
    grid_y = 134
    pitch = 15
    cell = 11

    for row, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        elements.append(
            f'  <text x="32" y="{grid_y + row * pitch + 9}" fill="{palette["muted"]}" font-size="10">{name}</text>'
        )

    last_month = None
    last_label_col = -4
    for col, week in enumerate(weeks):
        days = week["contributionDays"]
        if not days:
            continue
        date = dt.date.fromisoformat(days[0]["date"])
        if not placeholder and date.month != last_month and col - last_label_col >= 3:
            elements.append(
                f'  <text x="{grid_x + col * pitch}" y="124" fill="{palette["sub"]}" font-size="10">{date.strftime("%b")}</text>'
            )
            last_label_col = col
        last_month = date.month

        for day in days:
            x = grid_x + col * pitch
            y = grid_y + day["weekday"] * pitch
            count = day["contributionCount"]
            unit = "contribution" if count == 1 else "contributions"
            title = (
                "Setup preview — no activity data"
                if placeholder
                else f'{day["date"]}: {count} {unit}'
            )
            level = day["contributionLevel"]
            color = levels[level]
            stroke_attr = f' stroke="{palette["cell_stroke"]}" stroke-width="0.6"' if level == "NONE" else ""
            elements.append(
                f'  <rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{color}"{stroke_attr}><title>{title}</title></rect>'
            )

    if placeholder:
        elements.extend([
            f'  <rect x="245" y="156" width="410" height="58" rx="10" fill="{palette["overlay_bg"]}" stroke="{palette["overlay_border"]}"/>',
            f'  <text x="450" y="180" text-anchor="middle" fill="{palette["text"]}" font-size="12.5" font-weight="600">Awaiting first sync</text>',
            f'  <text x="450" y="199" text-anchor="middle" fill="{palette["sub"]}" font-size="11">Run the profile-activity workflow to load live GitHub data.</text>',
        ])

    footer = (
        "Setup preview · No statistics generated yet"
        if placeholder
        else f"Updated {sync_date} UTC · GitHub GraphQL API"
    )
    elements.append(f'  <text x="32" y="253" fill="{palette["muted"]}" font-size="10.5">{footer}</text>')
    elements.append(f'  <text x="752" y="253" text-anchor="end" fill="{palette["muted"]}" font-size="10.5">Less</text>')
    for idx, level in enumerate(["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]):
        lx = 760 + idx * 15
        stroke_attr = f' stroke="{palette["cell_stroke"]}" stroke-width="0.6"' if level == "NONE" else ""
        elements.append(
            f'  <rect x="{lx}" y="243" width="11" height="11" rx="2.5" fill="{levels[level]}"{stroke_attr}/>'
        )
    elements.append(f'  <text x="868" y="253" text-anchor="end" fill="{palette["muted"]}" font-size="10.5">More</text>')
    elements.append("</g>")
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--placeholder", action="store_true")
    parser.add_argument("--input-json", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "assets" / "profile",
    )
    args = parser.parse_args()

    username = os.environ.get("PROFILE_USERNAME", "shakil42051")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", username):
        parser.error("PROFILE_USERNAME must be a valid GitHub username.")
    if args.placeholder and args.input_json:
        parser.error("Choose either --placeholder or --input-json.")

    try:
        if args.placeholder:
            profile = None
        else:
            if args.input_json:
                payload = json.loads(args.input_json.read_text(encoding="utf-8"))
            else:
                token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
                if not token:
                    parser.error("Set GH_TOKEN or GITHUB_TOKEN for a live update.")
                payload = fetch_profile(username, token)
            profile = validate_profile(payload, username)

        sync_date = dt.datetime.now(dt.timezone.utc).date().isoformat()
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for theme in ("dark", "light"):
            svg = render_card(profile, username, sync_date, theme)
            target = args.output_dir / f"activity-{theme}.svg"
            target.write_text(svg, encoding="utf-8", newline="\n")
    except urllib.error.HTTPError as error:
        print(f"GitHub API request failed (HTTP {error.code}); existing cards were preserved.", file=sys.stderr)
        return 1
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"Profile update failed: {error}", file=sys.stderr)
        return 1

    mode = "setup preview" if args.placeholder else "GitHub API data"
    print(f"Wrote activity-dark.svg and activity-light.svg ({mode}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
