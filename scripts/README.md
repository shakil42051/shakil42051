# Profile activity generator

`update_profile.py` builds `assets/profile/activity.svg` from GitHub contribution data using only Python’s standard library. The workflow in `.github/workflows/profile-activity.yml` runs it daily and on demand.

The generator uses GitHub’s automatic workflow token. It preserves the existing card if an API request fails. No personal access token is required.
