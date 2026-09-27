<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WikdSolvemProbler/WikdSolvemProbler/HEAD/assets/panel-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/WikdSolvemProbler/WikdSolvemProbler/HEAD/assets/panel-light.svg">
  <img width="100%" alt="A coderprint panel: new lines written, commit activity and the language mix over time" src="https://raw.githubusercontent.com/WikdSolvemProbler/WikdSolvemProbler/HEAD/assets/panel-dark.svg">
</picture>

# coderprint

Your code's fingerprint on your GitHub profile: how much you actually wrote, how often, and in what, across every repository you own, private ones included. It runs as a GitHub Action inside your own profile repository, so nothing outside GitHub ever reads your code.

## What it shows

- **New lines written** over the window you pick. Under the total, 52 bars split the chart's span: each slice's lines rise in green and its commits hang below in red, each scaled to its own peak, and the biggest bursts of work carry their own totals. The bars start on the day your real work did.
- **Commits** on every branch, **active days** and your **longest** and **current streak** (days with a commit, counted in your own time zone when your profile shows one, see below), and how many **languages** you wrote. One green dot at a time hops along these rows, and each number lights as the dot reaches it.
- **The language mix over time.** Days before today run along a log scale, so last week gets room and last year still fits. Quiet stretches are veiled by how little evidence they rest on, and the mix eases across them instead of jumping. The stream flows into a column that is also the legend: your eight biggest languages by name, the rest as Other.
- **A red Pareto line** over the stream: the running share of every line in the chart, from 0% at its left edge to 100% today. It draws itself, fast where you wrote fast and slow across quiet time.
- **Five themes** (Paper, Sepia, Sage, Oxblood and Ink), each drawn twice: a light version for visitors in light mode and a dark one, near-black and softly glowing, for dark mode. Everyone sees the same theme on a given day, and the five take turns daily, unless you pin one with the `theme` input.
- **What you're playing on Spotify, or the track you last played on Apple Music**, optionally, merged into the same card in its colors.
- **A layout for phones.** On a screen 540 CSS pixels wide or less, your README shows a compact panel instead: the same numbers, bars, chart, legend and motion, 360 wide and stacked, so nothing that must be read shrinks to a few pixels. With the relay (step 4 below) it comes merged over a strip showing your music; with a music card beside the panel and no relay, phones get the two side by side, as on a desktop.

Motion only ever adds to a finished panel. A visitor whose device asks for reduced motion sees none of it, and a viewer that never starts animations still sees the whole panel. Screen readers get the numbers in words, and so does the image's alt text in your README.

## How it counts

A file version counts once, the first time its exact content appears in any of your repositories or branches. Copies, moves, merges, branch landings and imports from one repository to another reuse content that already exists, so they add nothing. A commit that adds more than 500 new files is treated as bringing in an existing codebase and skipped, as are commits by bots. Vendored folders, generated output, lockfiles and data files never count. Commits dated in the future (a wrong clock) are left out.

A file's language comes from its extension, and an extension coderprint does not know counts as Other. The chart names at most eight languages; the rest, and any language under 1% of the window's lines, are drawn as Other, so the legend lists only what can be seen. The languages count in the stats covers every language coderprint recognizes in your window, named on the chart or not, except Markdown, which is prose.

Days are your own, if and only if your public profile already says where you are. coderprint reads two things any visitor can see: the local time GitHub shows on your profile, if you turned that on, and your profile's location, looked up in a table of cities built from [GeoNames](https://www.geonames.org). The time zone always wins; the location can only choose among the zones with that offset today, which decides daylight saving for past days. A location that could mean places in different zones, such as "Santa Clara" (California or Cuba), "USA" or "SF / NYC", is not guessed at: days then fall at your shown offset, fixed for every past day so its daylight saving is ignored, or with no time zone shown, in UTC. Nothing else is asked for, and the zone is never printed or written anywhere.

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
      - uses: WikdSolvemProbler/coderprint@bfdd634fbf60b70ec398bf6040a03fedbc2b975c # v1.0.1
        with:
          token: ${{ steps.app.outputs.token }}
          window: all
          force: ${{ inputs.force && 'true' || 'false' }}
```

Run it once from the Actions tab. It writes `assets/panel-light.svg` and `assets/panel-dark.svg`, their compact versions for phones (`assets/panel-compact-light.svg` and `assets/panel-compact-dark.svg`), `assets/cards.json` and, unless a music card sits beside the panel, an empty `assets/blank.svg`. It puts the panel at the top of your `README.md` between two markers, `<!-- coderprint:start -->` and `<!-- coderprint:end -->`. Everything else in your README stays as it is; only the text between the markers is ever rewritten. It refreshes daily.

Unless a music card sits beside the panel, the markers hold two pictures, one for light mode and one for dark, and GitHub shows only the one that matches your visitor's. Each shows the compact panel on a screen 540 CSS pixels wide or less and the wide one otherwise. The empty `blank.svg` fills the other picture, so a visitor who chose a fixed theme on GitHub, rather than their device's, still sees the matching panel.

**3. Optional: Spotify or Apple Music.** Pick one; a run with both set stops with an error. The music card then sits beside the panel.

- **Spotify.** Sign in at [spotify-github-profile.kittinanx.com](https://spotify-github-profile.kittinanx.com), copy the `uid` from the widget address it gives you, and add `spotify-uid: YOUR_UID` to the step above.
- **Apple Music.** Its card has no "now playing": it shows the track you played last. Sign in with your Apple ID at [music-profile.rayriffy.com](https://music-profile.rayriffy.com). The first time, the site sends you on to `/connect`, which is a 404 page, so open [music-profile.rayriffy.com/dashboard/link](https://music-profile.rayriffy.com/dashboard/link) yourself and choose **Connect with Apple Music**. Then open [music-profile.rayriffy.com/dashboard](https://music-profile.rayriffy.com/dashboard), copy the uid from the Markdown snippet it shows (everything after `uid=`), and add `apple-music-uid: YOUR_UID` to the step above. If the card later shows an error, your Apple Music session has expired: open `/dashboard/link` and connect again.

  That service is run by its author, Phumrapee Limpianchop, not by coderprint. It keeps your Apple ID email address, your Apple Music user token, an Apple refresh token and the network address you connected from; each time it draws your card it records the address that asked for it (your relay's, or without the relay GitHub's image proxy); and when it cannot read your track, its error log can hold your music token. Like the Spotify uid, your uid is public once it is in your repository, and anyone who has it can see the track you played last.

**4. Optional: merge them into one card.** Two images load at two different moments, and neither music card matches your theme: Spotify's never does in light mode, and Apple Music's keeps colors of its own. The relay in this repository merges them into one image, recoloring the Spotify card to the day's theme or drawing your Apple Music track in it, and serves it from a cache so it appears at once, even though Apple Music's card takes about 4 to 6 seconds to draw.

- [Deploy your own copy to Vercel](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FWikdSolvemProbler%2Fcoderprint&env=CODERPRINT_USERS&envDescription=Your%20GitHub%20login) (the free Hobby plan is plenty). Vercel copies this repository into a new one under your account; keep it private, as the license requires. When GitHub asks where to install Vercel, choose **Only select repositories**: Vercel is granted the repository it creates and nothing else of yours. Set `CODERPRINT_USERS` to your GitHub login. The relay refuses anyone not on that list, so nobody else can spend your quota.
- Add `relay: https://YOUR-PROJECT.vercel.app/api/card` to the step above, with the domain listed under your project's **Settings → Domains**. The longer per-deployment addresses Vercel also shows sit behind a Vercel login, so GitHub could not load the card from them.

The relay serves the card at `/api/card` and nothing else: the `public` folder, which holds only a `robots.txt`, is all a visitor can reach, so the rest of your copy stays private.

## Options

| Input | Default | What it does |
| --- | --- | --- |
| `token` | required | Reads your repositories. Use the App token from step 1. |
| `window` | `all` | The span everything covers: `all`, `10y`, `5y`, `3y`, `2y` or `12m`. The chart starts at your oldest real work inside it, so it never shows empty time. |
| `theme` | none | Pins one theme: `paper`, `sepia`, `sage`, `oxblood` or `ink`. Visitors in light mode still get its light version and those in dark mode its dark one. Left out, the five take turns, one a day. |
| `spotify-uid` | none | Shows what you're playing on Spotify. Set this or `apple-music-uid`, not both. |
| `apple-music-uid` | none | Shows the track you last played on Apple Music (step 3). Set this or `spotify-uid`, not both. |
| `relay` | none | Your relay's card address, to merge the panel and the music card into one image. |
| `mark` | none | Your own watermark, drawn faintly behind the chart: SVG path data with straight segments only, filled even-odd, up to 48 KB. Pass it from a secret (`mark: ${{ secrets.CODERPRINT_MARK }}`) so the path data never sits in your repository. It sits turned 10 degrees, as part of the panel's design. It is drawn into the panel as pixels, merged with the background, so like any picture what is drawn can still be seen and traced. |
| `force` | `false` | Redraw even if fewer repositories are visible than last time. Otherwise the old panel is kept, since that usually means a deleted repository or a token that lost access. |
| `commit` | `true` | Commit and push the panel and README when they change. |

## Privacy

Action logs on a public repository are public, so coderprint never prints or writes a repository name, a file path or a commit message. The panel and `assets/cards.json` hold totals only. Clones live in a temporary folder that is deleted when the run ends, including when it is stopped by the time limit.

## Credits

The Spotify card is [kittinan/spotify-github-profile](https://github.com/kittinan/spotify-github-profile) by [Kittinan](https://github.com/kittinan), under the MIT License. On a desktop the relay only recolors it to match your theme; on a phone it redraws the song, artist and cover in a strip of its own. What it shows comes from that project.

The Apple Music track comes from [rayriffy/apple-music-github-profile](https://github.com/rayriffy/apple-music-github-profile) by Phumrapee Limpianchop ([rayriffy](https://github.com/rayriffy)), under the GNU Affero General Public License 3.0. coderprint draws its own Apple Music card from the song, artist and cover that project's card names, and copies none of that project's code.

The place table, `places.tsv.gz`, is [GeoNames](https://www.geonames.org) data, trimmed to names, populations and time zones, with names folded to plain lowercase and a few common alternative names added by `tools/build_places.py`, and is licensed, like that data, under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). GeoNames provides the data as is, without warranty or any representation of accuracy, timeliness or completeness.

## License

Copyright 2026 Peter Shiller. coderprint is licensed under the [PolyForm Strict License 1.0.0](LICENSE.md): you may install and run it for noncommercial purposes, but not change it or share it. [NOTICE.md](NOTICE.md) adds one permission, to deploy a private, unmodified copy of the relay for your own profile, and reserves the name, the wordmark, the panel's design and the author's mark.
