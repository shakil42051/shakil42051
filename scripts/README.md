# Profile activity generator

`update_profile.py` generates `assets/profile/activity-dark.svg` and `assets/profile/activity-light.svg` from GitHub's GraphQL contribution calendar using only Python's standard library.

The GitHub Actions workflow in `.github/workflows/profile-activity.yml` runs it daily and on manual dispatch using GitHub's built-in `GITHUB_TOKEN`. If an API request fails, the existing cards are left untouched.
