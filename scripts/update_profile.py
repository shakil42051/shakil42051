#!/usr/bin/env python3
"""Render an honest, self-hosted GitHub activity card using only Python's stdlib."""

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

COLORS = {
    "NONE": "#18283b",
    "FIRST_QUARTILE": "#174f52",
    "SECOND_QUARTILE": "#227c76",
    "THIRD_QUARTILE": "#35b8a5",
    "FOURTH_QUARTILE": "#5eead4",
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
        raise ValueError("GitHub returned a GraphQL error; the existing card was preserved.")
    profile = payload.get("data", {}).get("user")
    if not profile or profile.get("login", "").lower() != username.lower():
        raise ValueError("No matching GitHub user was returned; the existing card was preserved.")
    calendar = profile["contributionsCollection"]["contributionCalendar"]
    if not 1 <= len(calendar["weeks"]) <= 54:
        raise ValueError("Unexpected contribution calendar length.")
    counts = [calendar["totalContributions"], profile["followers"]["totalCount"],
              profile["repositories"]["totalCount"]]
    dates = set()
    for week in calendar["weeks"]:
        if len(week["contributionDays"]) > 7:
            raise ValueError("Unexpected number of days in a week.")
        for day in week["contributionDays"]:
            parsed = dt.date.fromisoformat(day["date"])
            if day["date"] in dates or day["weekday"] != (parsed.weekday() + 1) % 7:
                raise ValueError("Invalid or repeated contribution date.")
            dates.add(day["date"])
            if day["contributionLevel"] not in COLORS:
                raise ValueError("Unknown contribution level.")
            counts.append(day["contributionCount"])
    if not all(isinstance(value, int) and not isinstance(value, bool) and value >= 0
               for value in counts):
        raise ValueError("Invalid activity counts.")
    if not dates:
        raise ValueError("GitHub returned an empty calendar.")
    return profile


def render_card(profile, username, sync_date):
    placeholder = profile is None
    escaped_name = html.escape(username)
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="350" viewBox="0 0 1200 350" role="img" aria-labelledby="title desc">',
        f'<title id="title">GitHub activity for {escaped_name}</title>',
        '<desc id="desc">Awaiting first sync. Run the included GitHub Actions workflow to load real data.</desc>'
        if placeholder else f'<desc id="desc">Contribution calendar and public profile metrics from the GitHub API. Last synced {sync_date} UTC.</desc>',
        '<defs><linearGradient id="edge"><stop stop-color="#5eead4"/><stop offset="1" stop-color="#a5b4fc"/></linearGradient></defs>',
        '<rect x="0.5" y="0.5" width="1199" height="349" rx="20" fill="#0b1220" stroke="#25354a"/>',
        '<path d="M24 1 H1176" stroke="url(#edge)" stroke-width="2"/>',
        '<g font-family="Segoe UI,Arial,sans-serif">',
        '<text x="36" y="37" fill="#5eead4" font-size="13" font-weight="700" letter-spacing="2">ACTIVITY / THE LONG GAME</text>',
        f'<text x="1164" y="37" text-anchor="end" fill="#9cabc0" font-size="12">@{escaped_name}</text>',
    ]
    if placeholder:
        metrics = [("—", "CONTRIBUTIONS · LAST YEAR"), ("—", "ACTIVE DAYS"),
                   ("—", "PUBLIC REPOSITORIES"), ("—", "FOLLOWERS")]
        last_sunday = dt.date(2026, 1, 4)
        weeks = [{"contributionDays": [
            {"date": (last_sunday + dt.timedelta(days=7 * week + day)).isoformat(),
             "weekday": day, "contributionCount": 0, "contributionLevel": "NONE"}
            for day in range(7)]} for week in range(53)]
    else:
        calendar = profile["contributionsCollection"]["contributionCalendar"]
        weeks = calendar["weeks"]
        active = sum(day["contributionCount"] > 0 for week in weeks
                     for day in week["contributionDays"])
        metrics = [(f'{calendar["totalContributions"]:,}', "CONTRIBUTIONS · LAST YEAR"),
                   (str(active), "ACTIVE DAYS"),
                   (f'{profile["repositories"]["totalCount"]:,}', "PUBLIC REPOSITORIES"),
                   (f'{profile["followers"]["totalCount"]:,}', "FOLLOWERS")]
    for x, (value, label) in zip([36, 352, 642, 946], metrics):
        elements.append(f'<text x="{x}" y="84" fill="#eef3ff" font-size="32" font-weight="700">{value}</text>')
        elements.append(f'<text x="{x}" y="107" fill="#9cabc0" font-size="11" letter-spacing="1">{label}</text>')
    for row, name in [(1, "M"), (3, "W"), (5, "F")]:
        elements.append(f'<text x="36" y="{170 + row * 20}" fill="#71849d" font-size="10">{name}</text>')
    last_month = None
    for col, week in enumerate(weeks):
        days = week["contributionDays"]
        if not days:
            continue
        date = dt.date.fromisoformat(days[0]["date"])
        if not placeholder and date.month != last_month:
            elements.append(f'<text x="{76 + col * 20}" y="144" fill="#9cabc0" font-size="11">{date.strftime("%b")}</text>')
        last_month = date.month
        for day in days:
            x, y = 76 + col * 20, 158 + day["weekday"] * 20
            title = "Setup preview — no activity data" if placeholder else f'{day["date"]}: {day["contributionCount"]} contributions'
            color = COLORS[day["contributionLevel"]]
            elements.append(f'<rect x="{x}" y="{y}" width="14" height="14" rx="3" fill="{color}"><title>{title}</title></rect>')
    if placeholder:
        elements.extend([
            '<rect x="350" y="193" width="510" height="72" rx="14" fill="#101d2f" stroke="#38536b"/>',
            '<text x="605" y="221" text-anchor="middle" fill="#5eead4" font-size="15" font-weight="700" letter-spacing="1">AWAITING FIRST SYNC</text>',
            '<text x="605" y="245" text-anchor="middle" fill="#c3cedf" font-size="12">Enable the included workflow to load real GitHub activity.</text>',
        ])
    footer = "SETUP PREVIEW · No statistics have been generated yet." if placeholder else f"GitHub API · Last synced {sync_date} UTC"
    elements.append(f'<text x="36" y="326" fill="#9cabc0" font-size="11">{footer}</text>')
    elements.append('<text x="1010" y="326" text-anchor="end" fill="#9cabc0" font-size="11">Less</text>')
    for index, color in enumerate(COLORS.values()):
        elements.append(f'<rect x="{1022 + index * 20}" y="315" width="14" height="14" rx="3" fill="{color}"/>')
    elements.append('<text x="1130" y="326" fill="#9cabc0" font-size="11">More</text>')
    elements.append('</g></svg>')
    return "\n".join(elements) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--placeholder", action="store_true")
    parser.add_argument("--input-json", type=Path)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "assets/profile/activity.svg")
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
        svg = render_card(profile, username, sync_date)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg, encoding="utf-8", newline="\n")
    except urllib.error.HTTPError as error:
        print(f"GitHub API request failed (HTTP {error.code}); the existing card was preserved.", file=sys.stderr)
        return 1
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"Profile update failed: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {args.output.name} ({'setup preview' if args.placeholder else 'GitHub API data'}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
