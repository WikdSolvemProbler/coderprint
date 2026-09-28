# Contributing to coderprint

Anyone can contribute: a bug report, a fix, a clearer sentence in the README, a new idea, or a challenge to a decision already made. Every contribution follows one rule, set out below, and every participant follows the [Code of Conduct](CODE_OF_CONDUCT.md).

One thing never goes in a public issue or pull request: a security problem goes through the private route in [SECURITY.md](SECURITY.md). Questions are welcome in issues, as [SUPPORT.md](SUPPORT.md) describes.

## The rule

1. Every contribution (a pull request, and every issue that proposes a change) answers the five Ws:
   - **Who** is affected, or who benefits.
   - **What** changes, or what is wrong.
   - **When** it happens, or when it should apply.
   - **Where**, meaning which files, parts of the card or settings.
   - **Why**, meaning the reason and the problem it solves.
2. A contribution that questions any of the owner's logic (a design decision, a default, a formula, a threshold, a claim in the docs) must also give **How**: either how it suggests the logic be improved, or how the pull request improves it.
3. Such a challenge must also give **Evidence**: at least one source that backs the reasoning, such as a peer-reviewed research paper, a survey or systematic review, a standard or specification, official documentation, or a reproducible measurement or benchmark with the script that produced it. Cite each with a link or a Digital Object Identifier (DOI) and one or two sentences on what it shows and how it applies. Opinion alone is not evidence.

A sentence or two per answer is enough. The questions exist so that the maintainer can act on a contribution without a round of follow-up questions, not to make contributing slow.

## A good challenge, worked through

coderprint skips any commit that adds more than 500 new files of code, treating it as an existing codebase brought in rather than code written (`IMPORT_FILES` in `coderprint.py`). Suppose you think 500 is wrong. "500 is too high" is an opinion and will be closed. A pull request that challenges it well reads like this:

- **Who:** profile owners who scaffold projects with generators that write several hundred files in one commit.
- **What:** those scaffolds count as written code, so the panel's new lines total is inflated.
- **When:** on every run whose window includes such a commit.
- **Where:** `IMPORT_FILES` in `coderprint.py`, and the "How it counts" section of the README.
- **Why:** the panel claims to count code a person wrote; a generated scaffold is not that.
- **How:** lower the threshold to the value the measurement below supports, and state the new value in the README.
- **Evidence:** a script added in the pull request, linked at its commit (for example `https://github.com/YOUR-NAME/coderprint/blob/YOUR-COMMIT/tools/count_new_files.py`), that counts new files per commit across a stated list of public repositories, with its output table; and what the generators themselves document writing, such as Django's `startproject` (https://docs.djangoproject.com/en/stable/ref/django-admin/#startproject) and Vite's project templates (https://vite.dev/guide/). The pull request says which figure sets the new threshold and why.

The same shape works in an issue when you do not want to write the change yourself.

## What counts as evidence

Counts:

- A peer-reviewed paper, a survey or a systematic review, cited by DOI or a stable link.
- A standard or specification, such as a World Wide Web Consortium (W3C) recommendation.
- Official documentation from the maker of the tool or service in question.
- A measurement or benchmark that anyone can rerun: the script, its input, and its output, linked so that others can find them.

Does not count on its own:

- Opinion, preference or taste, however widely shared.
- "Everyone does it this way" without a source showing that they do and that it works.
- A link with no sentence on what it shows or how it applies here.
- A secondary summary, such as a blog post or an answer from a chat assistant, unless it leads to a primary source you then cite.
- A source that studies a different problem, unless you explain why its finding carries over.

## Why this rule

The five Ws are old. Rudyard Kipling named them, with How, as "six honest serving-men" in "The Elephant's Child" (*Just So Stories*, 1902, [Project Gutenberg](https://www.gutenberg.org/files/2781/2781-h/2781-h.htm)), and Michael C. Sloan traces the list of circumstances behind them to Aristotle ("Aristotle's *Nicomachean Ethics* as the Original Locus for the *Septem Circumstantiae*," *Classical Philology* 105(3), 2010, pages 236 to 251, DOI [10.1086/656196](https://doi.org/10.1086/656196)).

Research on bug reports and templates supports asking for structured, relevant information:

- Bettenburg, Just, Schröter, Weiss, Premraj and Zimmermann surveyed developers and reporters of Apache, Eclipse and Mozilla (466 responses) and found "an information mismatch between what developers need and what users supply"; developers rated steps to reproduce, stack traces and test cases most helpful ("What Makes a Good Bug Report?", Foundations of Software Engineering 2008, pages 308 to 318, DOI [10.1145/1453101.1453146](https://doi.org/10.1145/1453101.1453146)). That is why the bug form asks When as the steps that make the bug happen.
- Sülün, Saçakçı and Tüzün studied 350 issue templates in 100 projects on GitHub, over 1.9 million issues. Issues in projects with a template were resolved in 103.18 days against 381.02 in projects without one, with 4.32 comments against 4.95, and form templates did better still ("An Empirical Analysis of Issue Templates Usage in Large-Scale Projects on GitHub," Association for Computing Machinery (ACM) *Transactions on Software Engineering and Methodology*, 2024, DOI [10.1145/3643673](https://doi.org/10.1145/3643673)). The study is observational, so it shows association, not cause.

The same research carries a warning. Li, Yu, Wang, Lei, Wang and Wang found that after projects adopted templates, issues took longer to resolve, and both contributors and maintainers complained of "excessive and irrelevant information request" ("To Follow or Not to Follow: Understanding Issue/Pull-Request Templates on GitHub," Institute of Electrical and Electronics Engineers (IEEE) *Transactions on Software Engineering*, 2023, DOI [10.1109/TSE.2022.3224053](https://doi.org/10.1109/TSE.2022.3224053)). That is why each answer here is a sentence or two, and why How and Evidence are asked only of a challenge.

The How and Evidence parts follow established practice:

- Tsay, Dabbish and Herbsleb found that discussion of pull requests on GitHub turns on whether the problem is the right one and whether the solution is correct, and that core members and outside stakeholders alike discussed, and sometimes built, alternative solutions ("Let's Talk About It: Evaluating Contributions through Discussion in GitHub," Foundations of Software Engineering 2014, DOI [10.1145/2635868.2635882](https://doi.org/10.1145/2635868.2635882)). A challenge that arrives with its alternative puts that discussion on the table from the start.
- Dybå, Kitchenham and Jørgensen describe evidence-based software engineering as five steps: turn the problem into an answerable question, search for the best evidence, appraise it, combine it with practical experience, and evaluate the result ("Evidence-based Software Engineering for Practitioners," *IEEE Software*, 2005, [preprint](https://cms.simula.no/sites/default/files/publications/Dyba.2005.1.pdf)).
- The [Rust Request for Comments (RFC) template](https://raw.githubusercontent.com/rust-lang/rfcs/master/0000-template.md) asks for rationale, alternatives and prior art; [Python Enhancement Proposal (PEP) 1](https://peps.python.org/pep-0001/) asks for alternate designs, related work and important objections; and Michael Nygard's architecture decision records ask for context and every consequence, "not just the 'positive' ones" ([15NOV2011](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions)).

No study shows that the five Ws in particular improve outcomes. The rule rests on a long convention, on evidence that structured and relevant information helps, and on evidence that asking for too much hurts.

## Issues

Open an issue with one of the three forms: **Bugs** for a defect, **Question** for help or a question, and **Change or challenge** for a proposed change or a challenge to a decision. Blank issues are turned off so that every issue answers the rule; a question asks only what the question needs.

Never paste a token, a private key, or the name of a private repository. coderprint is built never to print or write a repository name, a file path or a commit message in its logs; if your log shows one, that is a security problem, so report it through [SECURITY.md](SECURITY.md) instead.

## Pull requests

1. Fork the repository and make your change on a branch of your fork.
2. Keep one change per pull request. Two unrelated fixes are two pull requests.
3. Fill in the template. It asks the five Ws, has a box to check if your pull request questions a decision or claim in coderprint, and then asks How and Evidence.
4. The **contribution check**, a workflow in this repository, reads your pull request's description every time you open, edit, reopen or push to the pull request. It fails when any of Who, What, When, Where or Why is empty, when the box line has been deleted, or when the box is checked and How is empty or Evidence cites no link or DOI. Text left inside the template's comment markers does not count as an answer, and neither does a placeholder such as "n/a" or "TBD". Edit the description to fix it; the check runs again. The check always runs as it is on `main`, so a pull request cannot change what it checks.

A pull request that passes the check still needs review. The check confirms that the questions are answered, not that the answers are right.

## Setting up and running the tests

The relay (`api/card.js` and `lib/compose.js`) and its tests need Node.js 22 or later and nothing else: `package.json` lists no dependencies, so there is nothing to install.

```sh
timeout -k 10s 300s npm test
```

This runs `node --test` over `test/*.test.js`.

The generator's synthetic regression checks need Python 3.12 or later, Git, and Node.js 22 or later. They build temporary Git histories and replace GitHub responses locally; they do not need a token or access to another account. From the repository root, run:

```sh
timeout -k 10s 1800s python test/py/run.py
```

The runner gives each Python test script a five-minute deadline and exits with an error when one fails or times out. The full run has a 30-minute deadline in CI. The commands above use Linux's `timeout`; on Windows, launch them through the installed process guard with the same outer deadlines.

The generator, `coderprint.py`, needs Python 3 and only its standard library, plus the `gh` command signed in to GitHub, and `git`. Without a time zone database (Python older than 3.9, or Windows without the `tzdata` package) it counts days in Coordinated Universal Time (UTC) or at the profile's fixed offset. Without the `design` folder it draws in a plain grey look. It reads its settings from environment variables (`CARDS_OWNER`, `CARDS_WINDOW`, `CARDS_THEME` and the others `action.yml` passes); `GH_TOKEN` is optional locally, since without it `gh`'s own sign-in answers. It writes into the folder it runs in: the panel files under `assets/`, and a block in `README.md`. Run a live check from a scratch copy of a profile repository, never from this one. The synthetic checks cover the generator's main paths without GitHub; for a change that needs live verification, say in your pull request exactly what you ran and what you compared. Do not imply that a second account was checked unless it was.

## Conventions

These are the conventions new contributions follow, as recent commits do.

- **Commit messages.** A short subject saying what the commit does, then paragraphs of prose saying what changed and why, then a last paragraph that starts `Checked:` and says what you ran and what it showed. For example, from this repository's history: subject "Turn the watermark 10 degrees as part of the design, not a setting", closing with "Checked: the generator's own checks pass with no failures, and the relay's tests pass."
- **A test for every relay fix.** A fix to the relay comes with a test that fails on the code before it and passes after, and the `Checked:` paragraph says so. A fix to the generator says exactly what you ran and what you compared.
- **Line endings.** Every tracked text file is stored with line feed (LF) line endings. Do not change line endings, and do not reformat lines your change does not touch.
- **Comments say why.** A comment explains a reason, a limit or a source, not what the next line does. Where a comment rests on outside documentation, it names the page and the date it was read, as `api/card.js` does.
- **Privacy.** The generator never prints or writes a repository name, a file path or a commit message, because Actions logs on a public repository are public. Keep it that way.
- **Few moving parts.** The generator uses only the Python standard library, `gh` and `git`. The relay has no dependencies, and `lib/compose.js` touches no network, file system or environment. A change that adds a dependency or breaks that separation questions a decision, so it gives How and Evidence.

## Licensing of contributions

coderprint's code is under the [coderprint Noncommercial License 1.0.0](LICENSE.md), so you may change it and fork it for noncommercial purposes, a contribution included. Its design is under [design/LICENSE.md](design/LICENSE.md), which lets a changed copy use the design only while you prepare and test a change you propose here. [NOTICE.md](NOTICE.md) explains both.

coderprint is sold to companies as well as shared, so every contribution comes with rights that let it be sold too.

**Your license to the owner.** When you submit a contribution (a pull request, a commit, or code or text in an issue or comment that you mark with the words "I contribute this under CONTRIBUTING.md"), you keep your copyright and grant Peter Shiller, and Peter Shiller's successors and assigns, a perpetual, worldwide, nonexclusive, royalty-free, irrevocable and transferable license to use, copy, change, make new works from, sublicense, relicense and distribute your contribution, under the project's licenses, under commercial licenses, or under any other terms. The owner's review of your contribution, and its distribution with your name in the history if it is merged, is the consideration for this grant. If your contribution is covered by a patent you can license, you grant the same people a license to that patent on the same terms, for coderprint and works based on it. You also state that the contribution is your own work, or that you have the right to submit it under these terms, and that no employer or anyone else holds a claim that conflicts with this grant. If you contribute as part of your job or with an employer's resources, your employer must hold or grant these rights: say so in the pull request and name the person at your employer who agreed.

**Sign-off.** Sign off every commit with `git commit -s`, which adds a line like `Signed-off-by: Your Name <you@example.com>` to the message; `git commit --amend -s` adds it to your last commit. In this repository a sign-off means you accept the terms in this section. If you commit through GitHub's web editor, type the `Signed-off-by:` line into the commit message yourself. A pull request whose commits are not all signed off is not merged.

**The design.** The `design` folder takes no outside changes. To propose a change to the look, open a **Change or challenge** issue.
