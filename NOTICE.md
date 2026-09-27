# Notice

Copyright 2026 Peter Shiller. All rights reserved, except as licensed in [LICENSE.md](LICENSE.md) under the PolyForm Strict License 1.0.0.

## Additional permission

In addition to that license, you may deploy one unmodified copy of this repository's relay (the `api` and `lib` folders) to a hosting account you control, keeping that copy private, solely so that it serves the card for your own GitHub profile. This permission does not extend to changing the relay or to making your copy available to anyone else.

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

## Reserved

The name coderprint, its wordmark (wordmark.svg), the visual design of the panel it draws, and the author's own mark are not licensed. No permission is granted to use any of them, except as they appear in the panels the software draws for your own profile.
