# Notice

Copyright 2026 Peter Shiller. All rights reserved, except as licensed below.

## What is licensed how

- **The code**, everything in this repository outside the `design` folder and the third-party parts below, is licensed under the PolyForm Noncommercial License 1.0.0 in [LICENSE.md](LICENSE.md), with the additional permissions below.
- **The design**, the `design` folder (the themes, the chart's colors and the coderprint wordmark), is licensed only under [design/LICENSE.md](design/LICENSE.md). Without it, the code draws in a plain look of its own.
- **Third-party parts** keep their own terms, set out at the end of this notice.

## Why

coderprint is one project. Its code is open to read, run, change and fork for any noncommercial purpose, and its look, its name and its marks belong to it, so a copy has to become something else rather than pass for coderprint. Sprawl is the opposite of integration: the way to change coderprint is to join it.

A coderprint card is its owner's own resume, published by their choice. It is never an instrument for measuring people who have not been told.

## Additional permissions

These add to LICENSE.md; they take nothing away from it.

1. **Your own profile.** Anyone may use coderprint to draw a card for their own GitHub profile and publish it there, whatever their work, their employer or their reason, including looking for work. That use is a permitted purpose under LICENSE.md.
2. **Your own relay.** Anyone may deploy a copy of the relay, the `api` and `lib` folders, to serve the card for their own GitHub profile, and let anyone view the card it serves.

## Commercial use

Any other use that is not a permitted purpose under LICENSE.md, for example a company running coderprint or software built from it, needs a commercial license from Peter Shiller, at a price. Ask at peter.shiller@pipeeko.com. No license is ever granted for running coderprint, or anything built from it, over employees', contractors' or candidates' accounts or data without telling each of them first, in writing.

## Contributions

Contributions are accepted under the contributor terms in [CONTRIBUTING.md](CONTRIBUTING.md), which let Peter Shiller license them under these terms and under commercial licenses.

## Reserved

The name coderprint, the coderprint wordmark and the author's own mark (the watermark in the author's own cards, which he supplies through his own secret, not the `mark` input any installer may use for their own) are not licensed, except as design/LICENSE.md allows for the wordmark. The name and the marks identify coderprint as Peter Shiller's work.

## Third-party data

places.tsv.gz is GeoNames data (https://www.geonames.org), trimmed to names, populations and time zones, with names folded to plain lowercase and a few common alternative names added by tools/build_places.py, and is licensed under Creative Commons Attribution 4.0 (https://creativecommons.org/licenses/by/4.0/), not under the license above. GeoNames provides the data as is, without warranty or any representation of accuracy, timeliness or completeness.

## Third-party services

The music cards come, while coderprint runs, from services that are not part of it and are not covered by the license above: the Spotify card from kittinan/spotify-github-profile by Kittinan (https://github.com/kittinan/spotify-github-profile, MIT License), and the Apple Music track from rayriffy/apple-music-github-profile by Phumrapee Limpianchop (https://github.com/rayriffy/apple-music-github-profile, GNU Affero General Public License 3.0). coderprint includes no code from either project, except in the relay's tests: test/spotify-recent.svg is the Spotify card as that service served it, with the track and the images replaced by stand-ins, and test/fixtures.js imitates its markup. The card's template belongs to kittinan/spotify-github-profile, whose license notice follows. For Apple Music the relay reads only the song, the artist and the cover from that service's card and draws its own. Album art belongs to its rights holders, and Spotify and Apple Music are trademarks of their owners, which coderprint names only to say where a track comes from.

The vinyl disc shading and grooves in lib/compose.js are adapted from h-moi/home-assistant-vinyl-player, dist/vinyl-player-card.js at commit a669cff56e6ee8b27c12784fbb76c82e42433ffb (https://github.com/h-moi/home-assistant-vinyl-player/blob/a669cff56e6ee8b27c12784fbb76c82e42433ffb/dist/vinyl-player-card.js). The CSS treatment is translated to native SVG, with a larger artwork label, one shared disc for both card sizes, and motion enabled only when the viewer permits it. No Home Assistant runtime or playback code is included. That adaptation retains the following license:

MIT License

Copyright (c) 2026 Home Assistant community contributors

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
