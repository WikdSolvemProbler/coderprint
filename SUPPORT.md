# Support

coderprint has one maintainer and no paid support. Help happens in public, in this repository's issues, so the next person with the same problem finds the answer already written.

## Before you ask

Read the [README](README.md). Its **How it counts** section answers most questions about the numbers: why a copied or moved file adds nothing, why a commit that adds more than 500 new files is skipped, and why an extension coderprint does not know counts as Other. Its **Options** section explains the inputs a setup needs, including `force`, which you need when the panel stops updating because fewer repositories are visible than last time.

Then search the [existing issues](https://github.com/WikdSolvemProbler/coderprint/issues?q=is%3Aissue), open and closed.

## Asking a question or reporting a problem

[Open an issue](https://github.com/WikdSolvemProbler/coderprint/issues/new/choose) and pick the form that matches: **Question**, or **Bugs** for a bug in the panel or the relay. Include:

- **The version you run**: the tag or commit in your workflow's `uses: WikdSolvemProbler/coderprint@...` line.
- **The inputs you set**, with every secret removed.
- **The Action log lines around the failure.** coderprint itself never prints a repository name, a file path or a commit message, so its own lines are safe to paste. Read the lines from other steps before you paste them.
- **For the relay**: open your card address (`https://YOUR-PROJECT.vercel.app/api/card?user=YOURNAME&mode=dark`) in a browser. When the relay cannot build the card, it answers with one line of text saying why. Paste that line.

Never paste a token, your GitHub App's private key, your `mark` path data, or a Spotify or Apple Music user identifier (uid) you have not already committed. Anyone who has your Apple Music uid can see the track you played last.

## What this project does not support

- **Someone else's relay.** Each relay belongs to the person who deployed it, and it serves only the logins in its own `CODERPRINT_USERS` list. The maintainer cannot see or change another person's deployment; ask its owner.
- **Vercel accounts**: plans, quotas, domains and billing belong to Vercel.
- **The music cards themselves.** The Spotify card is [kittinan/spotify-github-profile](https://github.com/kittinan/spotify-github-profile) and the Apple Music card is [rayriffy/apple-music-github-profile](https://github.com/rayriffy/apple-music-github-profile). Sign-in problems, expired sessions and wrong tracks on those services go to their projects. A card that those services draw correctly and the relay merges wrongly is a coderprint bug.
- **GitHub itself**: creating GitHub Apps, Actions outages and GitHub's image proxy belong to [GitHub Support](https://support.github.com).
- **Changed copies.** The code's [license](LICENSE.md) lets you change coderprint for noncommercial purposes, but only coderprint as published here is supported. If you want coderprint to work differently, propose the change through [CONTRIBUTING.md](CONTRIBUTING.md).

[LICENSE.md](LICENSE.md), [design/LICENSE.md](design/LICENSE.md) and [NOTICE.md](NOTICE.md) are the terms of use. Issues are not the place for legal advice. For a commercial license, write to peter.shiller@pipeeko.com.

## What to expect

One person answers issues, and no response time is guaranteed. An issue that leaves out the version, the inputs or the log lines gets a request for them before anything else.

## Security

Never report a vulnerability in a public issue. [SECURITY.md](SECURITY.md) says how to report one privately.

## Conduct

The [Code of Conduct](CODE_OF_CONDUCT.md) applies in issues, pull requests and every other project space.
