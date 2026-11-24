#!/usr/bin/env python3
"""Render compact light and dark GitHub momentum waveform SVGs using only Python's stdlib."""

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

VALID_LEVELS = {
    "NONE",
    "FIRST_QUARTILE",
    "SECOND_QUARTILE",
    "THIRD_QUARTILE",
    "FOURTH_QUARTILE",
}

THEMES = {
    "dark": {
        "bg": "#0d1017",
        "border": "#232a38",
        "divider": "#1d2433",
        "panel": "#121722",
        "panel_border": "#21293a",
        "text": "#f1f4f8",
        "sub": "#8b95a7",
        "muted": "#646e82",
        "bar_zero": "#1c2433",
        "bar_low": "#0f766e",
        "bar_mid": "#10b981",
        "bar_high": "#34d399",
    },
    "light": {
        "bg": "#f7f6f2",
        "border": "#dcd9cf",
        "divider": "#e4e1d8",
        "panel": "#ffffff",
        "panel_border": "#dedbd0",
        "text": "#14171f",
        "sub": "#555d6e",
        "muted": "#757d8d",
        "bar_zero": "#e2dfd6",
        "bar_low": "#34d399",
        "bar_mid": "#10b981",
        "bar_high": "#059669",
    },
}


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


def render_card(profile, username, sync_date, theme_name):
    c = THEMES[theme_name]
    placeholder = profile is None
    escaped_name = html.escape(username)
    sans = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif"
    mono = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

    if placeholder:
        total_str, active_str, repos_str = "—", "—", "—"
        weekly_totals = [0] * 53
        start_label, end_label = "52w ago", "Today"
    else:
        calendar = profile["contributionsCollection"]["contributionCalendar"]
        weeks = calendar["weeks"]
        all_days = [day for week in weeks for day in week["contributionDays"]]
        active_days = sum(day["contributionCount"] > 0 for day in all_days)
        total_str = f'{calendar["totalContributions"]:,}'
        active_str = f"{active_days:,}"
        repos_str = f'{profile["repositories"]["totalCount"]:,}'
        weekly_totals = [
            sum(day["contributionCount"] for day in week["contributionDays"])
            for week in weeks
        ]
        first_date = dt.date.fromisoformat(all_days[0]["date"])
        last_date = dt.date.fromisoformat(all_days[-1]["date"])
        start_label = first_date.strftime("%b '%y")
        end_label = last_date.strftime("%b '%y")

    max_week = max(weekly_totals) if any(weekly_totals) else 1
    desc = (
        "Awaiting first sync."
        if placeholder
        else f"Weekly contribution momentum and live stats for @{escaped_name}. Synced {sync_date} UTC."
    )

    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="108" viewBox="0 0 900 108" role="img" aria-labelledby="act-title act-desc">',
        f'  <title id="act-title">Live GitHub Momentum — @{escaped_name}</title>',
        f'  <desc id="act-desc">{desc}</desc>',
        '  <defs>',
        '    <style>',
        '      @media (prefers-reduced-motion: reduce) { .anim { display: none; } }',
        '    </style>',
        '  </defs>',
        f'  <rect x="0.5" y="0.5" width="899" height="107" rx="12" fill="{c["bg"]}" stroke="{c["border"]}"/>',
        f'  <g font-family="{sans}">',
        '    <circle cx="30" cy="26" r="3.2" fill="#10b981">',
        '      <animate class="anim" attributeName="opacity" values="1;0.3;1" dur="2.4s" repeatCount="indefinite"/>',
        '    </circle>',
        f'    <text x="41" y="29.5" fill="{c["muted"]}" font-family="{mono}" font-size="10" font-weight="600" letter-spacing="1.1">WEEKLY MOMENTUM  ·  AUTO-SYNCED</text>',
        f'    <text x="26" y="61" fill="{c["text"]}" font-size="20" font-weight="700" letter-spacing="-0.4">'
        f'{total_str} <tspan fill="{c["sub"]}" font-size="12" font-weight="400" letter-spacing="0">contributions</tspan>'
        f'<tspan fill="{c["muted"]}" font-size="13" font-weight="400">  ·  </tspan>'
        f'{active_str} <tspan fill="{c["sub"]}" font-size="12" font-weight="400" letter-spacing="0">active days</tspan>'
        f'<tspan fill="{c["muted"]}" font-size="13" font-weight="400">  ·  </tspan>'
        f'{repos_str} <tspan fill="{c["sub"]}" font-size="12" font-weight="400" letter-spacing="0">repos</tspan>'
        '</text>',
        f'    <text x="26" y="85" fill="{c["sub"]}" font-size="11.5">Open to internships, entry-level roles &amp; collaborations</text>',
        '  </g>',
        f'  <rect x="496" y="14" width="388" height="80" rx="9" fill="{c["panel"]}" stroke="{c["panel_border"]}"/>',
    ]

    # Render 53 weekly waveform bars inside (510..870), baseline at y=73
    num_weeks = len(weekly_totals)
    start_x = 510.0
    pitch = 356.0 / max(num_weeks - 1, 1)
    baseline_y = 73.0
    max_bar_h = 44.0

    last_active_x = None
    last_active_top = None

    for idx, total in enumerate(weekly_totals):
        bx = round(start_x + idx * pitch, 2)
        if total == 0:
            bh = 4.0
            fill = c["bar_zero"]
            by = round(baseline_y - bh, 2)
            elements.append(
                f'  <rect x="{bx}" y="{by}" width="4.4" height="{bh}" rx="2" fill="{fill}">'
                f'<title>Week {idx + 1}: 0 contributions</title></rect>'
            )
        else:
            ratio = total / max_week
            bh = round(max(9.0, ratio * max_bar_h), 2)
            by = round(baseline_y - bh, 2)
            if ratio >= 0.66:
                fill = c["bar_high"]
            elif ratio >= 0.33:
                fill = c["bar_mid"]
            else:
                fill = c["bar_low"]
            delay = round((idx % 9) * 0.22, 2)
            unit = "contribution" if total == 1 else "contributions"
            elements.append(
                f'  <rect x="{bx}" y="{by}" width="4.4" height="{bh}" rx="2" fill="{fill}">'
                f'<animate class="anim" attributeName="opacity" values="0.72;1;0.72" dur="2.8s" begin="{delay}s" repeatCount="indefinite"/>'
                f'<title>Week {idx + 1}: {total} {unit}</title></rect>'
            )
            last_active_x = round(bx + 2.2, 2)
            last_active_top = round(by - 5.5, 2)

    if last_active_x is not None and not placeholder:
        elements.append(
            f'  <circle cx="{last_active_x}" cy="{last_active_top}" r="2.2" fill="#10b981">'
            '<animate class="anim" attributeName="r" values="1.8;3.6;1.8" dur="2s" repeatCount="indefinite"/>'
            '</circle>'
        )

    elements.append(
        f'  <text x="510" y="87" fill="{c["muted"]}" font-family="{mono}" font-size="9">{html.escape(start_label)}</text>'
    )
    elements.append(
        f'  <text x="870" y="87" text-anchor="end" fill="{c["muted"]}" font-family="{mono}" font-size="9">{html.escape(end_label)}</text>'
    )
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
