# Security policy

coderprint has two parts, and a vulnerability can live in either:

- **The Action** (`action.yml` and `coderprint.py`) runs in a user's own profile repository with a token that can read every repository they own, private ones included, and commits the panel back.
- **The relay** (`api/card.js` and `lib/compose.js`) is a function a user deploys to Vercel. It fetches the panel from the user's profile repository and a music card from a third-party service, sanitizes both, and serves the merged image to anyone who views that profile.

This policy says which versions get fixes, how to report a problem privately, what happens after you do, and what counts as a vulnerability here. It was written 26SEP2026.

## Automated security checks

The repository uses the following free checks. The workflows run on standard GitHub-hosted runners in this public repository; they do not need a paid scanner subscription or another GitHub account.

| Check | Coverage | When it runs |
| --- | --- | --- |
| CodeQL | Python, JavaScript, and GitHub Actions security analysis | Pushes and pull requests to `main`, weekly |
| zizmor and actionlint | Workflow security, syntax, and embedded shell checks | Every push and pull request to `main`, manually |
| Jazzer.js and fast-check | Coverage-guided and property-based fuzzing of hostile relay inputs | Every push and pull request to `main`, manually |
| Dependabot | Updates to pinned GitHub Actions and isolated fuzzing tools | Weekly update pull requests |
| Harden-Runner Community | Runner activity and network monitoring | First step of each workflow job |

GitHub's secret scanning, push protection, Dependabot alerts, and Dependabot security updates are also enabled, so leaked secrets and vulnerable dependencies are caught without a separate workflow.

Third-party actions are pinned to full commit hashes, and GitHub enforces full-SHA pins for actions used by this repository. The setting is recorded in [.github/actions-permissions.json](.github/actions-permissions.json). The actionlint download is verified against a fixed checksum. Each job has a finite deadline. Pull requests use the `pull_request` trigger for source scans, without application secrets, and checkouts do not persist credentials. The contribution check keeps its trusted-base `pull_request_target` behavior described in its source, and one inline zizmor exception covers that trigger: the job executes only its trusted default-branch checker with read-only permissions. The exception covers the trigger warning alone; the other workflow-security rules remain active. Reassess it if that workflow starts consuming executable content from a pull request.

CodeQL and zizmor findings appear in the repository's **Security and quality** tab. A successful CodeQL job alone does not prove there were no findings, which is why the merge rule below also covers it. actionlint and pull-request zizmor scans fail their jobs when they find problems. Fuzzing and the npm audit of its locked dependencies must pass too. Harden-Runner uses audit mode to establish a network baseline; it does not impose a repository-specific network allowlist.

The `nosemgrep` comments on `blob_id` and `EMPTY_BLOBS` mark the two places that keep SHA-1 to calculate Git object identifiers. These values must match Git's SHA-1 repository format; they are not used as cryptographic signatures. SHA-256 repositories already use their corresponding object format.

Dependabot opens update proposals for review; it does not merge them. The contribution-description requirements still apply to those pull requests. The application has no third-party Python or JavaScript runtime packages. Fuzzing tools are isolated under `test/fuzz`, with an npm lockfile, dependency auditing, and their own Dependabot update configuration. Add the appropriate package ecosystem if runtime dependencies are introduced.

Configuration and free-tier details: [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [zizmor](https://github.com/zizmorcore/zizmor-action), [actionlint](https://github.com/rhysd/actionlint), and [Harden-Runner Community](https://github.com/step-security/harden-runner#features-and-pricing-tiers).

## Protected main branch

`main` requires a pull request, passing regression and security checks from GitHub Actions, an up-to-date branch, resolved review conversations, and linear history. Force pushes and branch deletion are disabled. These requirements also apply to administrators. The applied settings remain recorded in [.github/branch-protection.json](.github/branch-protection.json). An additional public [repository ruleset](https://github.com/WikdSolvemProbler/coderprint/rules/24153446), recorded in [.github/main-ruleset.json](.github/main-ruleset.json), explicitly requires PRs and code scanning. Editing either file alone does not change GitHub's settings.

The 8 required checks are the regression suite, fuzzing, actionlint, zizmor, CodeQL for all three configured languages, and the contribution-description check.

The same active ruleset requires CodeQL to supply analysis and blocks its new findings at every severity. There are no bypass actors. GitHub applies this gate to findings whose entire location is in the pull-request diff; existing alerts still need separate attention. See [GitHub's code scanning merge protection](https://docs.github.com/en/code-security/concepts/code-scanning/merge-protection).

The public ruleset makes the PR requirement visible to read-only security scanners. Scorecard v5.5.0's limited view of classic protection cannot reliably detect a required PR with zero approving reviews; its repository-rules reader can. This removes the misleading suggestion that PRs are not required without claiming independent review. See [Scorecard's GitHub protection readers](https://github.com/ossf/scorecard/blob/v5.5.0/clients/githubrepo/branches.go).

This is currently a single-maintainer project. Pull requests and CI are required, but a second person's approval is not required: that would prevent the sole maintainer from merging their own work. This does not provide independent human review, and automated analysis is not represented as such. When another maintainer can review changes, increase the required approval count and enable approval of the latest push.

## Supported versions

Security fixes land on the `main` branch and ship as a new release. Only the latest commit on `main` and the newest release are supported. The README tells users to pin the Action to a full commit, so a fix to the Action reaches a user only when they move their pin to the new release, and a fix to the relay reaches them only when they update their own deployed copy to it. The advisory for each fix names the release to move to.

| Version | Supported |
| --- | --- |
| Latest commit on `main` | Yes |
| Newest release | Yes |
| Any older tag or commit | No |

## How to report

Report privately. Do not open a public issue, pull request or discussion about a vulnerability, and do not describe it in a commit message.

1. Open [the repository's private reporting form](https://github.com/WikdSolvemProbler/coderprint/security/advisories/new). You can also reach it from the repository's **Security and quality** tab by choosing **Report a vulnerability**.
2. Give it a title and a description. Those are the only required fields.
3. Choose **Submit report**. GitHub notifies the maintainer, and only you, the maintainer and the people added to the advisory can see it or its comments.

Never paste a real token, a GitHub App private key, a watermark's path data, or the name of a private repository into a report. Redact them. A report is easier to act on without them.

## What to include

Answer the five Ws that [CONTRIBUTING.md](CONTRIBUTING.md) asks of every contribution, and How to reproduce the problem. Keep each answer short.

- **What** goes wrong, in one sentence.
- **Where**: the file and function, and the input that reaches it: an Action input, a query parameter, a file in the profile repository, or a response from a music service.
- **When**: the commit or release tag you tested, and whether you ran the Action, the relay, or both.
- **Who** can exploit it, and who is harmed: the user who installed coderprint, a visitor to their profile, or someone else.
- **Why** it matters: what an attacker gains, such as a leaked token, a leaked private repository name, script running in a viewer, or the relay fetching a host it should not.
- **How** to reproduce it, with the smallest proof you can make: a crafted Scalable Vector Graphics (SVG) file, a `coderprint.json`, a request address, or a workflow input. If you have a fix in mind, say how you would make it.

## What happens next

| Step | Target |
| --- | --- |
| Acknowledge your report | Within 7 days |
| Confirm or decline it, with reasons | Within 30 days |
| Release a fix for a confirmed vulnerability | Within 90 days, sooner for a leaked token or a leaked private repository name |
| Publish the advisory | When the fix is released |

The maintainer keeps you told of progress in the advisory's comments. If a fix will take longer than 90 days, the maintainer says why and agrees a new date with you. If the maintainer misses these times and does not answer you, you may disclose the vulnerability yourself 90 days after you reported it. A confirmed vulnerability gets a GitHub security advisory, and a Common Vulnerabilities and Exposures (CVE) identifier when it meets the criteria for one.

The 90 day window follows the common practice the Open Source Security Foundation (OpenSSF) describes in its [maintainer guide](https://github.com/ossf/oss-vulnerability-guide/blob/main/maintainer-guide.md).

## What coderprint promises

A vulnerability is a way to break one of these promises. Each is kept in the code named beside it, and the relay's tests in `test/hardening.test.js` and `test/wellformed.test.js` pin down the sanitizer's behavior.

**The Action**

- It never prints or writes a repository name, a file path, a commit message or an email address. Action logs on a public repository are public, so a leak of any of these, above all the name of a private repository, is a vulnerability. The panels and `assets/coderprint.json` hold totals only, and only by whole days, so they never tell what time of day anyone worked; `coderprint.json` is public output built from the same totals the panels draw, and names no repository. A failed command reports only the program's name, never its arguments (`run` in `coderprint.py`).
- The token never appears on a command line. `git` receives it through an environment-only header (`git_auth`), and the README's setup gives it a GitHub App token limited to reading contents and metadata that expires within the hour.
- Organization scanning is opt-in. A personal card's identity stays personal, and organization commits require a linked owner identity, the owner's noreply address or an explicitly listed, non-conflicting address. Name matching and the sole-author fallback apply only to personally owned repositories. An exact `authored-imports` declaration can override the bulk-upload heuristic, but never those attribution or file exclusions; its public provenance is labeled as an owner declaration.
- In Actions, each organization uses its own read token. Git headers are scoped to the selected repository URL; inherited environment authentication headers are removed, and unrelated installation tokens are not passed to child processes. External template repositories outside the configured accounts are fetched anonymously. A configured organization that cannot be read preserves existing panels rather than publishing a partial refresh.
- The optional blended local refresh seals complete organization Git bundles, template and authorship evidence into an AES-GCM authenticated encrypted snapshot with the existing local `gh` sign-in. It belongs in a private personally owned store, excluded from contributions. The daily workflow decrypts in temporary storage and replays saved history beside live personal history through the same collector; it never fetches or queries the organizations. The key stays in a profile secret and a protected local file, never in a command argument or a Git/gh child environment. The authenticated owner, live numeric account ID, date, manifest fields, bundle hashes, refs and extraction bounds are checked. Missing or invalid evidence keeps the existing card. Publish the private store before the public profile; a failed local write requires reviewing local changes before retrying.
- Snapshot encryption uses the vetted `cryptography` AEAD implementation with a fresh nonce per write. Keys, decrypted histories and private selectors must never be committed or uploaded as workflow artifacts. Snapshot dependencies are version- and hash-pinned; the dependency installer receives no scan credentials or private snapshot selectors. The older organization-only helper remains available for a separate aggregate view, whose totals should not be added as if deduplicated across scopes.
- Every Action input reaches the script through an environment variable, never pasted into the shell script, so an input cannot run commands (`action.yml`).
- Each clone is deleted as soon as it has been read, and the temporary folder when the run ends, including when the time limit stops it, unless the `CLONE_CACHE` setting for local runs keeps them.
- It draws a card only for the account whose repository it runs in (`own_card_only`), so no one can run it from their repository over someone else's account.
- It reads the owner's public profile page only from `github.com` over Hypertext Transfer Protocol Secure (HTTPS), and refuses a redirect to any other host (`GitHubOnly`).
- The watermark is meant to come from a secret, and the Action never writes its path data to the repository. `mark_outline` accepts only straight segments, at most 48 kilobytes, with bounded coordinates.
- It writes only its own files under `assets` and the marked block of `README.md` (`profile/README.md` in an organization's `.github` repository), each through a temporary file of a fresh name, never through a link or outside the repository (`write_all`), and commits only those, named one by one, and the removal of its own old `cards.json` (`action.yml`).

**The relay**

- It serves only the logins listed in `CODERPRINT_USERS`, and serves no one when that setting is empty or missing (`isAllowed`). A login must be a valid GitHub login, and each parameter may appear once.
- It fetches only three fixed hosts: `raw.githubusercontent.com` for the user's own profile repository, `spotify-github-profile.kittinanx.com` and `music-profile.rayriffy.com`. It refuses every redirect, stops every fetch at a deadline, and stops reading a body at 2 mebibytes for an image and 256 kibibytes for `coderprint.json` or `cards.json`, so an upstream cannot exhaust its memory or time.
- It treats everything it fetches as hostile. `coderprint.json`, or for a profile drawn before it existed `cards.json`, is read as JavaScript Object Notation (JSON), and only valid colors and identifiers are taken from it (`readCards`). The panel and the Spotify card pass the sanitizer in `lib/compose.js` before any of their markup is served; from the Apple Music card the relay reads only the song, the artist and the cover, and draws its own markup.
- The sanitizer refuses any document that is not well-formed Extensible Markup Language (XML), or that nests too deep. It drops `script`, `iframe`, `frame`, `frameset`, `object`, `embed` and `meta` elements, every event handler attribute, `xml:base`, and `srcset`, `imagesrcset`, `ping` and `attributionsrc`. It keeps a link or source only when it points inside the document or at an embedded raster image in Portable Network Graphics (PNG), Joint Photographic Experts Group (JPEG), Graphics Interchange Format (GIF) or WebP format. It refuses a style block, and drops an attribute, holding Cascading Style Sheets (CSS) that imports, binds, or fetches anything outside the document, and an animation may not target a link or an event handler.
- Every card goes out with a Content Security Policy (CSP) of `default-src 'none'; img-src data:; style-src 'unsafe-inline'; sandbox` and `X-Content-Type-Options: nosniff`, so a card opened directly is inert even if something slipped past the sanitizer.
- It serves the card at `/api/card` and nothing else of the deployed copy but `robots.txt`.

## In scope

- Anything that breaks a promise above, in the latest commit on `main` or the newest release.
- Markup that runs script, fetches an outside address, or navigates the viewer after passing the sanitizer, in any browser GitHub supports.
- A way to make the relay serve a login outside `CODERPRINT_USERS`, fetch a host other than its three, follow a redirect, or read past its size limits.
- A leak of a token, of the watermark's path data, or of a private repository's name, a file path or a commit message, into a log, a committed file, a served card or an error message.
- An Action input, a repository's contents or a profile page that makes the Action run a command, write outside `assets` and the marked block of the profile README, or push to another repository.
- Setup instructions in the README that grant more access than coderprint needs, or pin a dependency with a published vulnerability.

## Out of scope

- **Other people's deployments.** A relay is deployed and run by each user. Test only your own deployment, and report a problem with someone else's to them. A flaw in the relay's code is in scope; a user's misconfiguration of their own copy is not.
- **The third-party music services.** Report a vulnerability in the Spotify card to [kittinan/spotify-github-profile](https://github.com/kittinan/spotify-github-profile), and one in the Apple Music card to [rayriffy/apple-music-github-profile](https://github.com/rayriffy/apple-music-github-profile). What those services keep about their users is described in the README. Markup from them that gets past coderprint's sanitizer is in scope here.
- **GitHub and Vercel.** Report problems in either platform to that platform.
- **Attacks that need a compromised account or leaked secret.** A report that starts from control of the user's GitHub account, write access to their profile repository, their Vercel account, or their GitHub App's private key describes what that control already gives. It is in scope only if it reaches further than that control does, for example markup in the profile repository that runs script in a visitor's browser.
- **Behavior the README documents.** The watermark is drawn as pixels and can be seen and traced, like any picture. A Spotify or Apple Music user identifier (uid) in a public repository lets anyone see what that account played. The panel's totals are public by design.
- Volume-based denial of service, spam, social engineering, physical attacks, and reports from automated scanners that show no working exploit.
- Missing hardening with no demonstrated impact, such as a header that would add nothing to the Content Security Policy above.

## Safe harbor

If you research in good faith and follow this policy, the maintainer treats your research as authorized and will not pursue legal action over it. This cannot authorize you to test anything the maintainer does not own.

Good faith means that you:

- test only against your own profile repository, your own GitHub App and your own relay deployment;
- do not read, keep or share anyone else's data, and stop and report at once if you come across any;
- do not degrade the relay or the music services for other users;
- give the maintainer the time set out above before you disclose.

## Credit

GitHub lists you as a credited reporter on the advisory for your report. The maintainer also names you in the release that fixes it, unless you ask to stay anonymous. coderprint pays no bounty.
