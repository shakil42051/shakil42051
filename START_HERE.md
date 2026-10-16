# Put your new profile on GitHub

This package is personalized for **Md. Shakil Ahmad Nahid** and the username **`shakil42051`** from your original README.

## 1. Upload the complete profile

1. Open or create the public repository **`shakil42051/shakil42051`**.
2. Copy the **contents** of this package into that repository's root. `README.md` must be at the root, beside `assets/`, `scripts/`, and `.github/`. Do not upload the ZIP itself or nest everything in an extra folder.
3. Commit the files. The profile README and both custom GIFs will work immediately.

GitHub requires a public repository whose name matches your username, with a nonempty root README. [Official setup guide](https://docs.github.com/en/account-and-profile/how-tos/profile-customization/managing-your-profile-readme).

## 2. Switch on the daily activity card

1. Make sure `.github/workflows/profile-activity.yml` is included in the upload. Some file pickers hide dot folders; create the file in GitHub's editor if necessary.
2. In the repository, open **Actions → Refresh profile activity → Run workflow**. Enable Actions if GitHub asks.
3. After the first successful run, `assets/profile/activity.svg` shows your actual contribution calendar, public repository count, and follower count.

The workflow uses GitHub's automatic `GITHUB_TOKEN`. **No personal token or extra secret is required.** The job requests `contents: write` to commit only the generated SVG. Repository or organization policies and branch protection may restrict that write; the Actions log will show an error if they do. GitHub's [token documentation](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token) explains the permissions.

The scheduled refresh is at **05:23 Bangladesh time** each day (23:23 UTC on the previous date). GitHub may delay scheduled runs and may disable schedules in inactive public repositories. You can always run it manually. [Scheduled workflow documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Until the first successful sync, the activity card deliberately shows **“Awaiting first sync”**, without invented statistics. If an update fails, the last generated card remains in place. The card's last-synced date makes stale data visible. All calendar and metric values are whatever the workflow token can see through GitHub's API.

## What's inside

| File | Purpose |
| --- | --- |
| `README.md` | Your complete profile |
| `assets/profile/hero.gif` | Original animated identity banner |
| `assets/profile/hero.png` | Still banner for reduced-motion preferences |
| `assets/profile/commit-invaders.gif` | Original pixel arcade animation |
| `assets/profile/commit-invaders.png` | Still arcade scene for reduced-motion preferences |
| `assets/profile/toolkit.svg` | Matching learning-stack graphic |
| `assets/profile/footer.svg` | Matching signature graphic |
| `assets/profile/contact-*.svg` | Matching contact buttons |
| `assets/profile/activity.svg` | Initial card, then real GitHub activity after syncing |
| `scripts/update_profile.py` | Python standard-library activity generator |
| `.github/workflows/profile-activity.yml` | Daily and manual activity updates |

The GIF is an **autoplay animation**, not a keyboard-controlled game. The **off-by-one boss** is a playable click-to-reveal challenge inside the README. It works with native `<details>` sections, so no JavaScript or external game service is needed.

All artwork, animations, and contact buttons are bundled locally. The profile does not rely on third-party image generators or statistics-card services.

## Keep it personal

- Add direct repository links to the project table when you publish those projects.
- Update your current learning goals as you make progress.
- If your GitHub username changes, update the README links, `PROFILE_USERNAME`, and the workflow's repository condition.
- The résumé's phone number, exact address, date of birth, and family details were left out of this public profile.

The Python generator supports `--placeholder` for the initial setup card and `--input-json path.json --output path.svg` for offline rendering of a saved GitHub GraphQL response. Normal workflow runs fetch data directly from `api.github.com`.
