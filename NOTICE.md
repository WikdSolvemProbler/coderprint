# Notice

Copyright 2026 Peter Shiller. All rights reserved, except as licensed below.

## What is licensed how

- **The code**, everything in this repository outside the `design` folder and the third-party parts below, is licensed under the coderprint Noncommercial License 1.0.0 in [LICENSE.md](LICENSE.md), with the additional permissions below.
- **The design**, the `design` folder (the themes, the chart's colors and the coderprint wordmark), is licensed only under [design/LICENSE.md](design/LICENSE.md). Without it, the code draws in a plain look of its own.
- **Third-party parts** keep their own terms, set out at the end of this notice.

## Why

coderprint is one project. Its code is open to read, run, change and fork for noncommercial purposes, and its look, its name and its marks belong to it, so a copy has to become something else rather than pass for coderprint. Sprawl is the opposite of integration: the way to change coderprint is to join it.

A coderprint card is its owner's own resume, published by their choice. It is never an instrument for measuring people who have not been told.

## Additional permissions

These add to LICENSE.md and are granted on all of its terms, its conditions, Violations and No Liability included; they take nothing away from it. Like every license in it, they never cover running coderprint over people who have not been told (LICENSE.md, People Who Have Not Been Told).

1. **Your own profile.** Anyone may use coderprint to draw a card for their own GitHub profile and publish it there, whatever their work, their employer or their reason, including looking for work. That use is a permitted purpose under LICENSE.md.
2. **Your own relay.** Anyone may deploy a copy of coderprint, the `design` folder unchanged included, to serve the relay (the `api` and `lib` folders) for their own GitHub profile, whatever their work, their employer or their reason, let anyone view the card it serves, and replace that copy with a newer unchanged release whenever one is published. That use is a permitted purpose under LICENSE.md.

## Commercial use

Any other use that is not a permitted purpose under LICENSE.md, for example a company running coderprint or software built from it, needs a commercial license from Peter Shiller, at a price. Ask at peter.shiller@pipeeko.com. A commercial license is a separate written agreement; where it and LICENSE.md differ, it governs for its licensee. Every commercial license carries the section People Who Have Not Been Told of LICENSE.md unchanged: none is ever granted for running coderprint, or anything built from it, over anyone's accounts, repositories, commits or data without telling each of those people first, in writing.

## Versions

Releases up to and including v1.1.0 (commit 86c226e) were published under the PolyForm Noncommercial License 1.0.0 and stay under it; that license is unchanged by anything here and has no section People Who Have Not Been Told. Every later release is under the coderprint Noncommercial License 1.0.0 in LICENSE.md. Each copy is governed by the LICENSE.md it came with.

## Contributions

Contributions are accepted under the contributor terms in [CONTRIBUTING.md](CONTRIBUTING.md), which let Peter Shiller license them under these terms and under commercial licenses.

## Reserved

The name coderprint, the coderprint wordmark and the author's own mark (the watermark in the author's own cards, supplied through the author's own secret, not the `mark` input any installer may use for their own) are not licensed, except as design/LICENSE.md allows for the wordmark. The name and the marks identify coderprint as Peter Shiller's work. You may say, truthfully, that a work is built on or forked from coderprint. You may not name a changed copy coderprint, present its cards as coderprint's, or put the wordmark on anything but cards drawn under design/LICENSE.md.

## Third-party data

places.tsv.gz is GeoNames data (https://www.geonames.org), trimmed to names, populations and time zones, with names folded to plain lowercase and a few common alternative names added by tools/build_places.py, and is licensed under Creative Commons Attribution 4.0 (https://creativecommons.org/licenses/by/4.0/), not under the license above. GeoNames provides the data as is, without warranty or any representation of accuracy, timeliness or completeness.

## Third-party services

The music cards come, while coderprint runs, from services that are not part of it and are not covered by the license above: the Spotify card from kittinan/spotify-github-profile by Kittinan (https://github.com/kittinan/spotify-github-profile, MIT License), and the Apple Music track from rayriffy/apple-music-github-profile by Phumrapee Limpianchop (https://github.com/rayriffy/apple-music-github-profile, GNU Affero General Public License 3.0). coderprint includes no code from either project, except in the relay's tests: test/spotify-recent.svg is the Spotify card as that service served it, with the track and the images replaced by stand-ins, and test/fixtures.js imitates its markup. The card's template belongs to kittinan/spotify-github-profile, whose license notice follows. For Apple Music the relay reads only the song, the artist and the cover from that service's card and draws its own. Album art belongs to its rights holders, and Spotify and Apple Music are trademarks of their owners, which coderprint names only to say where a track comes from.

The license notice of kittinan/spotify-github-profile, which covers the Spotify card's markup in the relay's tests:

```
MIT License

Copyright (c) 2020 Kittinan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
