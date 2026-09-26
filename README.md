<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WikdSolvemProbler/WikdSolvemProbler/HEAD/assets/panel-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/WikdSolvemProbler/WikdSolvemProbler/HEAD/assets/panel-light.svg">
  <img width="100%" alt="A coderprint panel: new lines written, commit activity and the language mix over time" src="https://raw.githubusercontent.com/WikdSolvemProbler/WikdSolvemProbler/HEAD/assets/panel-dark.svg">
</picture>

# coderprint

Your code's fingerprint on your GitHub profile: how much you actually wrote, how often, and in what, across every repository you own, private ones included. It runs as a GitHub Action inside your own profile repository, so nothing outside GitHub ever reads your code.

## What it shows

- **New lines written** over the window you pick, with a bar for each slice of it.
- **Commits** on every branch, **active days** and your **longest** and **current streak** (days with a commit, counted in UTC), and how many **languages** you wrote.
- **The language mix over time.** Days before today run along a log scale, so last week gets room and last year still fits. Quiet stretches are veiled by how little evidence they rest on, and the mix eases across them instead of jumping. The stream flows into a column that is also the legend.
- **Five themes** (Paper, Sepia and Sage for light mode, Oxblood and Ink for dark). Visitors get the one matching their mode, and the choice rotates daily.
- **What you're playing on Spotify**, optionally, merged into the same card and recolored to match it.

## How it counts

A file version counts once, the first time its exact content appears in any of your repositories or branches. Copies, moves, merges, branch landings and imports from one repository to another reuse content that already exists, so they add nothing. A commit that adds more than 500 new files is treated as bringing in an existing codebase and skipped, as are commits by bots. Vendored folders, generated output, lockfiles and data files never count. Commits dated in the future (a wrong clock) are left out.

## Install

**1. Make a read-only GitHub App.** It lets the Action read your private repositories with a token that expires within the hour, instead of a personal token that never does.

- Open `https://github.com/settings/apps/new?name=coderprint-YOURNAME&url=https://github.com/YOURNAME&public=false&webhook_active=false&contents=read&metadata=read`, replacing `YOURNAME`, and create the App.
- On the App's page, note the **Client ID** and **generate a private key**.
- **Install** the App on your account with **All repositories**, so new repositories are counted without revisiting it.
- In your profile repository (`YOURNAME/YOURNAME`), under Settings, Secrets and variables, Actions: add a variable `CODERPRINT_APP_CLIENT_ID` holding the Client ID, and a secret `CODERPRINT_APP_KEY` holding the whole private key file. Then delete the key file.

**2. Add the workflow** as `.github/workflows/coderprint.yml` in your profile repository:

```yaml
name: coderprint

on:
  schedule:
    - cron: "23 8 * * *"
  workflow_dispatch:
    inputs:
      force:
        description: "Redraw even if fewer repositories are visible than last time"
        type: boolean
        default: false

permissions:
  contents: write

concurrency:
  group: coderprint
  cancel-in-progress: false

jobs:
  panel:
    if: ${{ vars.CODERPRINT_APP_CLIENT_ID != '' }}
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - id: app
        uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0
        with:
          client-id: ${{ vars.CODERPRINT_APP_CLIENT_ID }}
          private-key: ${{ secrets.CODERPRINT_APP_KEY }}
          owner: ${{ github.repository_owner }}
          permission-contents: read
          permission-metadata: read
      - uses: WikdSolvemProbler/coderprint@745394105e833a7a2ef4829c8628557e5ebb17f9 # v1
        with:
          token: ${{ steps.app.outputs.token }}
          window: all
          force: ${{ inputs.force && 'true' || 'false' }}
```

Run it once from the Actions tab. It writes `assets/panel-light.svg`, `assets/panel-dark.svg` and `assets/cards.json`, and puts the panel at the top of your `README.md` between two markers, `<!-- coderprint:start -->` and `<!-- coderprint:end -->`. Everything else in your README stays as it is; only the text between the markers is ever rewritten. It refreshes daily.

**3. Optional: Spotify.** Sign in at [spotify-github-profile.kittinanx.com](https://spotify-github-profile.kittinanx.com), copy the `uid` from the widget address it gives you, and add `spotify-uid: YOUR_UID` to the step above. The Spotify card then sits beside the panel.

**4. Optional: merge them into one card.** Two images load at two different moments, and Spotify's never matches your theme in light mode. The relay in this repository merges them into one image, recolors the Spotify card to the day's theme, and serves it from a cache so it appears at once.

- [Deploy your own copy to Vercel](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FWikdSolvemProbler%2Fcoderprint&env=CODERPRINT_USERS&envDescription=Your%20GitHub%20login) (the free Hobby plan is plenty). Keep the repository it creates for you private, as the license requires, and set `CODERPRINT_USERS` to your GitHub login. The relay refuses anyone not on that list, so nobody else can spend your quota.
- Add `relay: https://YOUR-DEPLOYMENT.vercel.app/api/card` to the step above.

## Options

| Input | Default | What it does |
| --- | --- | --- |
| `token` | required | Reads your repositories. Use the App token from step 1. |
| `window` | `all` | The span everything covers: `all`, `10y`, `5y`, `3y`, `2y` or `12m`. The chart starts at your oldest real work inside it, so it never shows empty time. |
| `spotify-uid` | none | Shows what you're playing on Spotify. |
| `relay` | none | Your relay's card address, to merge panel and Spotify into one image. |
| `mark` | none | Your own watermark, drawn faintly behind the chart: SVG path data with straight segments only, filled even-odd, up to 48 KB. Pass it from a secret (`mark: ${{ secrets.CODERPRINT_MARK }}`) so the path data never sits in your repository. It is drawn into the panel as pixels, merged with the background, so like any picture what is drawn can still be seen and traced. |
| `mark-turn` | `0` | Degrees to turn the watermark. |
| `force` | `false` | Redraw even if fewer repositories are visible than last time. Otherwise the old panel is kept, since that usually means a deleted repository or a token that lost access. |
| `commit` | `true` | Commit and push the panel and README when they change. |

## Privacy

Action logs on a public repository are public, so coderprint never prints or writes a repository name, a file path or a commit message. The panel and `assets/cards.json` hold totals only. Clones live in a temporary folder that is deleted when the run ends, including when it is stopped by the time limit.

## Credits

The Spotify card is [kittinan/spotify-github-profile](https://github.com/kittinan/spotify-github-profile). The relay only recolors it to match your theme; everything it shows comes from that project.

## License

Copyright 2026 Peter Shiller. coderprint is licensed under the [PolyForm Strict License 1.0.0](LICENSE.md): you may install and run it for noncommercial purposes, but not change it or share it. [NOTICE.md](NOTICE.md) adds one permission, to deploy a private, unmodified copy of the relay for your own profile, and reserves the name, the wordmark, the panel's design and the author's mark.
