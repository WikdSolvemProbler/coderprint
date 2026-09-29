<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WikdSolvemProbler/WikdSolvemProbler/HEAD/assets/panel-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/WikdSolvemProbler/WikdSolvemProbler/HEAD/assets/panel-light.svg">
  <img width="100%" alt="A coderprint panel: lines of code written and still in use, commit activity and the language mix over time" src="https://raw.githubusercontent.com/WikdSolvemProbler/WikdSolvemProbler/HEAD/assets/panel-dark.svg">
</picture>

# coderprint

> **In development.** Code is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE.md). The [design license](design/LICENSE.md) applies separately.

Your code's fingerprint on your GitHub profile: how much you actually wrote, how often, and in what, across every repository you own, private ones included. It runs as a GitHub Action inside your own profile repository, so nothing outside GitHub ever reads your code.

## What it shows

- **Lines of code**, as four figures: how many of the lines you wrote in the window you pick are still **in use**, split into **prod** (production code) and **tests**, beside everything **written**. A ring and a bar show the same split as shares of what you wrote, production drawn bright and tests dimmer, and the ring's middle says what share you kept. For visitors who allow motion they tell it as a story, slowly enough to follow: both fill to everything written and glow red with its figure, fall back to what is in use and glow yellow, fall to production and glow green, then fill back in with tests, green again, the ring's middle giving each step's share.
- **Activity** under them: 52 bars split the chart's span, each slice's lines of code rising in green and its commits hanging below in red, each scaled to its own peak, and the biggest bursts of work carry their own totals. The bars start on the day your real work did and end on the day the card was drawn, so a card that has stopped refreshing shows its date.
- **Commits** on every branch, **active days** and your **longest** and **current streak** (days with a commit, counted in your own time zone when your profile shows one, see below), and how many **languages** each hold 1% or more of your lines of code, which the row calls `languages · 1%+`. One green dot at a time hops along these rows, and each number lights as the dot reaches it.
- **The language mix over time.** Days before today run along a log scale, so last week gets room and last year still fits. Quiet stretches are veiled by how little evidence they rest on, and the mix eases across them instead of jumping. The stream flows into a column that is also the legend: your eight biggest languages by name, the rest as Other.
- **A red Pareto line** over the stream: the running share of every line in the chart, from 0% at its left edge to 100% today. It draws itself, fast where you wrote fast and slow across quiet time.
- **Five themes** (Paper, Sepia, Sage, Oxblood and Ink), each drawn twice: a light version for visitors in light mode and a dark one, near-black and softly glowing, for dark mode. Everyone sees the same theme on a given day, and the five take turns daily, unless you pin one with the `theme` input.
- **What you're playing on Spotify, or the track you last played on Apple Music**, optionally, merged into the same card in its colors.
- **A layout for phones.** On a screen 540 CSS pixels wide or less, your README shows a compact panel instead: the same numbers, bars, chart, legend and motion, 360 wide and stacked, so nothing that must be read shrinks to a few pixels. With the relay (step 4 below) it comes merged over a strip showing your music; with a music card beside the panel and no relay, phones get the two side by side, as on a desktop.

Motion only ever adds to a finished panel. A visitor whose device asks for reduced motion sees none of it, and a viewer that never starts animations still sees the whole panel. Screen readers get the numbers and the bars' dates in words, and the image's alt text in your README gets the numbers.

## How it counts

coderprint reads every branch of every repository your account owns, forks left out; the `gh-pages` branch is read only when it is the default, and a tag on it does not bring it back in. It counts lines of code only. A blank line is not code, and neither is a line that is only a comment, recognized by each language's own comment syntax; a line of code with a comment after it is code, and so is every line of a string, whatever it holds. A Python docstring, or any string standing alone as a statement, is a comment. Each file is read whole, as its language reads it: Python by Python's own tokenizer, the C family and most other languages with their strings and character literals followed, so a comment opened after code on a line is seen and a comment nested in another is nested where the language nests them. A line added to a file reads as the whole new file reads it, so a line added inside a comment or a string opened further up counts, or not, exactly as it will at the head. A few languages whose strings cannot be followed line by line (shell scripts, Perl, Ruby, MATLAB and some others) are read by their comment syntax at the start of each line only, so there a comment opened after code on its line counts as code. Prose and data are never code: Markdown, TeX, YAML, TOML, plain text, the prose around the code of a literate source, notebooks (Jupyter's and Mathematica's), any file whose name or extension no language claims, and one whose extension several languages share and comment differently (`.pl`). A header (`.h`) is C, C++ or Objective-C, which all comment alike, and `.m`, `.fs` and `.v` are each shared by languages that comment compatibly, so their lines count, drawn as Other. `assets/coderprint.json` says how many lines of each figure rest on a fallback reading, such as a Python file its tokenizer cannot read.

**Written** is every line of code added in a new file version, and each file version counts once, the first time its exact content appears in any of your repositories or branches. Exact copies, moves, merges, branch landings and imports from one repository to another reuse content that already exists, so they add nothing, and a file moved to a new name while being edited adds only the lines it changed, even where git itself does not pair the two names (a move of more files than its rename limit, or a `.js` file rewritten as `.ts`). A block of three or more lines moved within one commit, inside its file or into another, adds nothing either (its text is compared spacing aside, so a block only re-indented is moved too), and a squash merge, or a rebase that reset its author dates, of a branch still kept adds only what the branch did not already write; no commit says it is a squash, so one is known by its lines, nearly all of them waiting on a kept branch. A copy, or a deleted file brought back, that changes even one line is a new file version, and every line of code it adds counts. A file version first committed under a name that does not count, such as a `.txt` file or one in `build/` or `vendor/`, never counts, even once it is renamed to one that does; committed under both at once, it counts. A rewrite of a line does count again; deleting a line takes nothing off what you wrote.

These counts have limits. A rebased copy of a branch that is still kept can count some work twice when too little of the original change remains for coderprint to recognize it. If a repository's line diffs cannot be read, coderprint falls back to Git's added-line totals for that repository, which can include comments and blanks; those lines add nothing to **in use**, and the data file and run log say this happened. For some languages whose strings cannot be followed reliably, the line reader uses the documented start-of-line comment rule above.

**In use** is read at the head of each repository's default branch: the lines of code standing there that you wrote in the window, where wrote means exactly the lines counted as written. Each written line counts in use at most once across all your repositories, so in use can never exceed written, and a file copied into a second repository, or a fork, is in use once. Every line is traced through its history: each file version is the version before it with its diff applied, so a line keeps the commit that added it, and it is yours when that commit's line was counted as written in the window. A line you wrote and later deleted is not in use; a line someone else wrote is not yours, even in your repository and however common its text, and neither is a line you wrote before the window; a line your formatter re-indented, a sweep renamed or a commit moved is still yours, whoever made the sweep or the move, since each hands the line it changes on to the line it leaves in its place, and so is a line a merge brought in from your branch. A line whose history cannot say, such as one only a merge's conflict resolution wrote, is matched by its text instead, spacing aside, against the written lines no traced line took; `assets/coderprint.json` says how many lines were traced and how many were matched by text. An archived repository's head is not in use, though its history still counts as written. A line is **test** code when its file sits in a tests folder (`tests`, `__tests__`, `spec`, `e2e` and the like) or is named as a test (`test_x.py`, `x_test.go`, `x.test.ts`, `XTest.java`), or in Rust, when it sits in a `#[cfg(test)]` module; every other line in use is **production**. A repository whose history cannot be read line by line counts its added lines whole, comments and blank lines included, adds nothing in use, is counted in `assets/coderprint.json`, and is warned of in the run's log; one whose default branch cannot be read at its head still counts the lines of code it wrote, adds nothing in use, and is counted there separately. An empty repository, or one holding only tags, has nothing in it to count.

What counts as yours, for both:

- **Only your own commits.** Commits whose author address belongs to another GitHub account are someone else's and add nothing: no lines, no commit, no active day. Your noreply addresses, under any login you have had, and every address linked to your account are yours; another account's noreply address never is. An address linked to no account counts as yours under your name or login, and in a repository where it is the only address with commits, bots aside, unless the name on it ends in the word "bot" or "agent", as a self-hosted bot's or a coding agent's own identity does ("Renovate Bot", "Cursor Agent"): that is automation. Your own linked addresses are other addresses here: a repository you created on github.com with a README already holds a commit from one, so an unlinked address committing there counts only under your name or login. A name a machine or a tutorial gives a commit, such as "root" or "Your Name", is nobody's, so it never makes another address yours. GitHub is asked about at most 1,000 addresses a run, those likeliest to matter first; one it was not asked about counts only under your name or login. A commit two of your repositories hold is yours if it is yours in either. Addresses are read as they were committed, not as a `.mailmap` rewrites them, since GitHub reads them so. List any other address you commit from in the `author-emails` input; one GitHub links to another account is ignored. A coding agent that commits under your own name and address is you. An organization's card counts every member; an organization installs coderprint in its `.github` repository, where the panel goes into `profile/README.md`, the organization's profile, and the relay does not serve organizations yet.
- **No automation.** Commits by bots, by a workflow (a `[bot]` committer, even when you are the author) or under names like "Automated" or "github-actions" are left out.
- **No reformatting.** A commit that changes ten or more files at once, each adding about as many lines as it deletes, adds nothing written for the files whose changed lines still read nearly as they did (a formatter, re-indenting, a line-ending change, an identifier renamed, imports sorted), and neither do commits listed in a repository's `.git-blame-ignore-revs`, whatever the case of their hashes. A file in such a commit that only gains lines, or whose lines were rewritten into different code, counts as written. The lines they touch stay yours in use, whoever committed the sweep: a formatter bot's, a collaborator's or your own workflow's.
- **Once per change.** The same change landed twice under new hashes (a cherry-pick, a rebase that kept the old branch, an amend still reachable from a tag) counts once: the same author, author second and subject, and most of the same lines of code. It is one commit, and of a second landing's lines only those the first did not count are written, such as a file an amend added or a line a conflict's resolution wrote. Different changes that share only the first three, such as one message committed in several repositories at once or the two halves of a split commit, each count.
- **Not what you started from.** A commit that adds more than 500 new files of code brings in an existing codebase, and so does a run of your commits to one repository, each adding 50 or more new files of code within an hour of the one before, that adds more than 500 in all, as uploading a project through github.com 100 files at a time does. Prose, data and files no language claims do not count toward the 500, and neither does a file the commit moved from one it deleted; a codebase brought in more slowly than that counts as written. Each such commit counts as a commit and an active day but adds no lines, written or in use, and `assets/coderprint.json` records the lines of code it held. The files of another account's template your repository was made from count as already written, and so do coderprint's own files in your relay copy.
- **Not generated or vendored.** Vendored folders, generated output, lockfiles, submodules, symbolic links and data files never count. Generated output is known by its folder (a build's `dist`, `build`, `out` or `coverage` folder at the top of a repository or of a module), by its name, and by a generator's mark in its first lines (`Code generated ... DO NOT EDIT`, `<auto-generated />`, a Django migration's header, or a page naming its site generator, which with two more like it marks its whole site). Vendored code is known by its folder (`node_modules`, `vendor`, `third_party`, `extern`, `external` or `deps` at a repository's top, WordPress's and Unity's plugins, and the like). Paths your repository's `.gitattributes` marks `linguist-vendored`, `linguist-generated` or `linguist-documentation` never count either, as GitHub's own language bar reads them, each file version judged by the attributes its own commit held. Commits dated in the future (a wrong clock) are left out.

A file's language comes from its name or extension. The chart names at most eight languages; the rest, and any language under 1% of the window's lines of code, are drawn as Other, so the legend lists only what can be seen. The languages count in the stats covers every language at 1% or more of your window's lines of code, named on the chart or not.

Every time is moved to the start of its day before anything is drawn, so nothing on the card tells what time of day you work. A repository that cannot be read, even on a second try, is left out and counted in `assets/coderprint.json`; if more than one, and more than a tenth of them, cannot be read, the previous panels are kept. A repository made from another account's template is left out and counted the same way when GitHub cannot list that template's files, and so is your relay copy when coderprint's own cannot be listed, since your code there could not be told from what came with it. When GitHub cannot be asked, even on a second try, whose an address is or which repositories were made from a template, the previous panels are kept, since the run could not tell your code from anyone else's. The run keeps time back from its limit for asking, so one that reads until its limit leaves out only the repositories it had no time for.

Days are your own, if and only if your public profile already says where you are. coderprint reads two things any visitor can see: the local time GitHub shows on your profile, if you turned that on, and your profile's location, looked up in a table of cities built from [GeoNames](https://www.geonames.org). The time zone always wins; the location can only choose among the zones with that offset today, which decides daylight saving for past days. A location that could mean places in different zones, such as "Santa Clara" (California or Cuba), "USA" or "SF / NYC", is not guessed at: days then fall at your shown offset, fixed for every past day so its daylight saving is ignored, or with no time zone shown, in UTC. Nothing else is asked for, and the zone is never printed or written anywhere.

## For machines

Everything the card says is also written as data, in `assets/coderprint.json`, so a program or a language model reading your profile never has to read pixels. It is built from the very values the panels are drawn from, not scraped from them, and the card itself does not change by a pixel.

- **What it holds.** The headline (`quantity`: written, in use, production, tests and the share kept), the stats (`activity`: commits, active days, both streaks, and the 52 slices the activity bars draw, with how much of the headline falls before the first of them), the language mix (`languages`: each language's lines and share, its lines in each slice, and the legend as the chart draws it), what was left out and why (`left_out`, whose `over` says whether each count covers the window or the whole history), and what was read (`scope`). Every headline and stats figure carries its value, its unit, whether it was counted from history (`measured`), computed from other figures (`derived`) or rounded as drawn (`display`), and a pointer into `definitions`, which says once what each term means, how it is counted and what it cannot tell. In use also says how many of its lines were traced through history (`traced_loc`) and how many were matched by text (`matched_by_text_loc`). The slices, the lines by slice and the legend give their provenance and definition once for each group; the counts in `scope` and `left_out`, and each language's `loc` (its lines of code) and `share` (of the lines of code written), are plain numbers named for what they count.
- **How it is found.** The README block holds a comment naming it, which GitHub keeps in the file and draws nothing for, and every panel names its address in its `<metadata>`.
- **What it never holds.** Source code, repository names, file names or paths, commit messages, email addresses, times of day or your time zone: aggregates only, by whole days, like the panels. The relay's colors and music sit apart, under `presentation`.
- **Stability.** The schema is `coderprint/1`. Within it fields are only ever added, so a reader should ignore any it does not know.

It replaces `cards.json`, which earlier versions wrote. coderprint removes its own old `cards.json` the first time it runs, known by the palettes and the count of repositories every earlier version wrote in it, and leaves any other file of that name alone. A relay copy deployed before this release reads only `cards.json`, so update your relay first (step 4).

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
      - uses: WikdSolvemProbler/coderprint@8824fe6d04670a875a8641079dc1e6f73c647168 # v1.2.1
        with:
          token: ${{ steps.app.outputs.token }}
          window: all
          force: ${{ inputs.force && 'true' || 'false' }}
```

Run it once from the Actions tab. It writes `assets/panel-light.svg` and `assets/panel-dark.svg`, their compact versions for phones (`assets/panel-compact-light.svg` and `assets/panel-compact-dark.svg`), `assets/coderprint.json` and, unless a music card sits beside the panel, an empty `assets/blank.svg`. It puts the panel at the top of your `README.md` between two markers, `<!-- coderprint:start -->` and `<!-- coderprint:end -->`. Everything else in your README stays as it is; only the text between the markers is ever rewritten. A marker counts only on a line of its own outside fenced code, so a README that quotes them keeps its text; a README with two pairs, or half a pair, one saved in Unicode Transformation Format (UTF) 16 or 32 rather than UTF-8, or one named other than `README.md` stops the run with an error before any repository is read, rather than lose any of your text. It refreshes daily.

Unless a music card sits beside the panel, the markers hold two pictures, one for light mode and one for dark, and GitHub shows only the one that matches your visitor's. Each shows the compact panel on a screen 540 CSS pixels wide or less and the wide one otherwise. The empty `blank.svg` fills the other picture, so a visitor who chose a fixed theme on GitHub, rather than their device's, still sees the matching panel.

**3. Optional: Spotify or Apple Music.** Pick one; a run with both set stops with an error. The music card then sits beside the panel.

- **Spotify.** Sign in at [spotify-github-profile.kittinanx.com](https://spotify-github-profile.kittinanx.com), copy the `uid` from the widget address it gives you, and add `spotify-uid: YOUR_UID` to the step above.
- **Apple Music.** Its card has no "now playing": it shows the track you played last. Sign in with your Apple ID at [music-profile.rayriffy.com](https://music-profile.rayriffy.com). The first time, the site sends you on to `/connect`, which is a 404 page, so open [music-profile.rayriffy.com/dashboard/link](https://music-profile.rayriffy.com/dashboard/link) yourself and choose **Connect with Apple Music**. Then open [music-profile.rayriffy.com/dashboard](https://music-profile.rayriffy.com/dashboard), copy the uid from the Markdown snippet it shows (everything after `uid=`), and add `apple-music-uid: YOUR_UID` to the step above. If the card later shows an error, your Apple Music session has expired: open `/dashboard/link` and connect again.

  That service is run by its author, Phumrapee Limpianchop, not by coderprint. It keeps your Apple ID email address, your Apple Music user token, an Apple refresh token and the network address you connected from; each time it draws your card it records the address that asked for it (your relay's, or without the relay GitHub's image proxy); and when it cannot read your track, its error log can hold your music token. Like the Spotify uid, your uid is public once it is in your repository, and anyone who has it can see the track you played last.

**4. Optional: merge them into one card.** Two images load at two different moments, and neither music card matches your theme: Spotify's never does in light mode, and Apple Music's keeps colors of its own. The relay in this repository merges them into one image, recoloring the Spotify card to the day's theme or drawing your Apple Music track in it, and serves it from a cache so it appears at once, even though Apple Music's card takes about 4 to 6 seconds to draw.

- [Deploy your own copy to Vercel](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FWikdSolvemProbler%2Fcoderprint&env=CODERPRINT_USERS&envDescription=Your%20GitHub%20login) (the free Hobby plan is plenty). Vercel copies this repository into a new one under your account; keep it private, since the design folder it copies is licensed only for coderprint's own use. When GitHub asks where to install Vercel, choose **Only select repositories**: Vercel is granted the repository it creates and nothing else of yours. Set `CODERPRINT_USERS` to your GitHub login. The relay refuses anyone not on that list, so nobody else can spend your quota.
- Add `relay: https://YOUR-PROJECT.vercel.app/api/card` to the step above, with the domain listed under your project's **Settings → Domains**. The longer per-deployment addresses Vercel also shows sit behind a Vercel login, so GitHub could not load the card from them.
- **Updating from an earlier release: the relay first.** Your relay copy is updated apart from the Action, so update it before you move the Action's pin: bring this release's files into the repository Vercel made, which redeploys it. A relay copy from before this release reads only `cards.json`, which this release replaces with `assets/coderprint.json` and removes, so once the Action had run the old relay would answer every card with an error. This release's relay reads `coderprint.json`, and `cards.json` while your profile still has one, so it serves your card both before and after the Action moves.

The relay serves the card at `/api/card` and nothing else: the `public` folder, which holds only a `robots.txt`, is all a visitor can reach, so the rest of your copy stays private.

## Options

| Input | Default | What it does |
| --- | --- | --- |
| `token` | required | Reads your repositories. Use the App token from step 1. |
| `owner` | Your repository's owner | The account whose card is drawn. It must own the repository running this Action; for an organization, run it from that organization's `.github` repository. |
| `window` | `all` | The span everything covers: `all`, `10y`, `5y`, `3y`, `2y` or `12m`. The chart starts at your oldest real work inside it, so it never shows empty time. |
| `theme` | none | Pins one theme: `paper`, `sepia`, `sage`, `oxblood` or `ink`. Visitors in light mode still get its light version and those in dark mode its dark one. Left out, the five take turns, one a day. |
| `spotify-uid` | none | Shows what you're playing on Spotify. Set this or `apple-music-uid`, not both. |
| `apple-music-uid` | none | Shows the track you last played on Apple Music (step 3). Set this or `spotify-uid`, not both. |
| `relay` | none | Your relay's card address, to merge the panel and the music card into one image. |
| `mark` | none | Your own watermark, drawn faintly behind the chart: SVG path data with straight segments only, filled even-odd, up to 48 KB. Pass it from a secret (`mark: ${{ secrets.CODERPRINT_MARK }}`) so the path data never sits in your repository. It sits turned 10 degrees, as part of the panel's design. It is drawn into the panel as pixels, merged with the background, so like any picture what is drawn can still be seen and traced. |
| `author-emails` | none | Addresses you commit from that are not linked to your GitHub account, separated by commas, spaces or new lines, each bare or as `Name <address>`, so their commits count as yours. One GitHub links to another account is ignored, and the log says how many were. |
| `time-limit` | `1100` | Seconds the drawing step may run, from `300` to `86400`. Keep it under the job's `timeout-minutes`; a repository that cannot be read in time is left out and counted. |
| `force` | `false` | Redraw even if fewer repositories are visible than last time. Otherwise the old panel is kept, since that usually means a deleted repository or a token that lost access. |
| `commit` | `true` | Commit and push the panel and README when they change. |

## Privacy

Action logs on a public repository are public, so coderprint never prints or writes a repository name, a file path, a commit message or an email address. The panel and `assets/coderprint.json` hold totals only, by whole days. Each clone is deleted as soon as it has been read, and the temporary folder when the run ends, including when it is stopped by the time limit (on GitHub's own runners; a stopped run on your own machine can leave it behind).

What the card does publish: for every repository it counts, private ones included, the language mix, the lines and the days worked. `assets/coderprint.json` and the run's log also give how many repositories it counted, so anyone who counts your public ones can tell how many are private, and how many commits by others and by automation it left out. Installing the App on **Only select repositories** keeps the others out entirely. Every refresh is a commit to your public profile repository, so earlier panels stay in its history.

## Credits

The Spotify card is [kittinan/spotify-github-profile](https://github.com/kittinan/spotify-github-profile) by [Kittinan](https://github.com/kittinan), under the MIT License. On a desktop the relay only recolors it to match your theme; on a phone it redraws the song, artist and cover in a strip of its own. What it shows comes from that project.

The Apple Music track comes from [rayriffy/apple-music-github-profile](https://github.com/rayriffy/apple-music-github-profile) by Phumrapee Limpianchop ([rayriffy](https://github.com/rayriffy)), under the GNU Affero General Public License 3.0. coderprint draws its own Apple Music card from the song, artist and cover that project's card names, and copies none of that project's code.

The place table, `places.tsv.gz`, is [GeoNames](https://www.geonames.org) data, trimmed to names, populations and time zones, with names folded to plain lowercase and a few common alternative names added by `tools/build_places.py`, and is licensed, like that data, under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). GeoNames provides the data as is, without warranty or any representation of accuracy, timeliness or completeness.

## License

Copyright 2026 Peter Shiller. In short:

- **The code** is under the [PolyForm Noncommercial License 1.0.0](LICENSE.md): read it, run it, change it and fork it for any noncommercial purpose. [NOTICE.md](NOTICE.md) adds that anyone may use coderprint on their own profile and run their own relay, whatever their job.
- **The design**, the themes, colors and wordmark in `design/`, is under [its own license](design/LICENSE.md): it goes unchanged with coderprint as published here. A copy that changes coderprint draws in the plain look, or in its own.
- **Companies** need a commercial license, at a price: ask at peter.shiller@pipeeko.com. None is ever granted for running coderprint over people who have not been told.
- **Your card is yours.** coderprint only ever reports on the account whose repository it runs in, and reading a card someone chose to publish is always fine.
- **Contributions** come under the terms in [CONTRIBUTING.md](CONTRIBUTING.md).

Why: sprawl is the opposite of integration. coderprint is one project, worth joining rather than copying, and a card is its owner's resume, never someone else's yardstick.
