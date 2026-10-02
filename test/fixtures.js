// Small stand-ins for the upstream documents, shaped like the real ones.
import { readFileSync } from 'node:fs';
import { VINYL_TEXTURE } from '../lib/vinyl-texture.js';

// Ignore only the exact first-party texture when checking that hostile provider images were refused.
export function withoutVinylTexture(svg) {
  return svg.replace(/<image\b[^>]*data-vinyl-texture="true"[^>]*\/>/g, (image) => {
    if (!image.includes(`href="${VINYL_TEXTURE}"`)) throw new Error('Unexpected record texture');
    return '';
  });
}

// A 1x1 PNG, standing in for the widget's logo and cover art.
export const PIXEL =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';

export const PANEL_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="576" height="445" viewBox="0 0 576 445" role="img" aria-label="New lines written">
<style>@media (prefers-reduced-motion: no-preference){@keyframes breathe{50%{opacity:.45}}.now{animation:breathe 1.8s ease-in-out infinite}}</style>
<defs><pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" stroke="#f4efe8" stroke-opacity=".035" fill="none"/></pattern></defs>
<rect width="576" height="445" rx="10" fill="#100f0e"/><rect width="576" height="445" rx="10" fill="url(#grid)"/>
<circle class="now" cx="40" cy="40" r="3" fill="#53b14f"/>
<text x="16.0" y="437.0" font-family="'IBM Plex Mono', monospace" font-size="7.5" fill="#625e59">PRIVATE REPOS INCLUDED · EACH LINE COUNTED ONCE</text>
</svg>
`;

// The generator's portrait panel for phones, cut down the same way. Its root's size and viewBox can be
// varied, and extra markup goes in the middle; viewBox: null leaves the viewBox out.
export function compactPanelSvg({ width = '360', height = '662', viewBox = `0 0 ${width} ${height}`, extra = '' } = {}) {
  const box = viewBox === null ? '' : ` viewBox="${viewBox}"`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"${box} role="img" aria-label="New lines written">
<style>@media (prefers-reduced-motion: no-preference){@keyframes breathe{50%{opacity:.45}}.now{animation:breathe 1.8s ease-in-out infinite}}</style>
<defs><pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" stroke="#f4efe8" stroke-opacity=".035" fill="none"/></pattern></defs>
<rect width="360" height="662" rx="10" fill="#100f0e"/><rect width="360" height="662" rx="10" fill="url(#grid)"/>
<circle class="now" cx="40" cy="40" r="3" fill="#53b14f"/>${extra}
<text x="14.0" y="622.0" font-family="'IBM Plex Mono', monospace" font-size="8" fill="#625e59">NORMALIZED · BY TYPE · EACH LINE COUNTED ONCE</text>
</svg>
`;
}

export const COMPACT_PANEL_SVG = compactPanelSvg();

// The status, artist and song are inserted verbatim, so a test can pass markup the upstream failed to
// escape; so are the cover and logo URLs.
export function spotifySvg({
  status = 'Now playing on',
  artist = 'Mura Masa',
  song = 'Love$ick (feat. A$AP Rocky)',
  cover = PIXEL,
  logo = PIXEL,
  extra = '',
} = {}) {
  return `<svg width="320" height="445" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-labelledby="cardTitle" role="img">
  <title id="cardTitle">Now playing on Spotify</title>
  <foreignObject width="320" height="445">
    <style>
      div { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif; }
      .container { background-color: #100f0e; border-radius: 10px; padding: 10px 10px }
      .playing { color: #53b14f; font-weight: bold; }
      .artist { color: #fff; font-weight: bold; font-size: 20px; }
      .song { color: #b3b3b3; font-size: 16px; }
      .bar { background: #53b14f; animation: sound 0ms -800ms linear infinite alternate; }
      @keyframes sound { 0% { opacity: .35; height: 3px; } 100% { opacity: 1; height: 22px; } }
    </style>
    <div xmlns="http://www.w3.org/1999/xhtml" class="container">
        <div class="playing">${status} <img class="logo" src="${logo}" /></div>
        <div class="artist">${artist}</div>
        <div class="song">${song}</div>
        <div id='bars'><div class='bar'></div><div class='bar'></div><div class='bar'></div></div>
        ${extra}
          <a href="{}" target="_BLANK">
            <center>
              <img src="${cover}" width="300" height="300" class="cover" />
            </center>
          </a>
    </div>
  </foreignObject>
</svg>`;
}

// A real capture of the widget (theme default) showing a recently played track, with the track and both
// images swapped for the stand-ins above and nothing else changed: it leaves #bars empty, though its style
// still places all 75 bars.
export const RECENT_SVG = readFileSync(new URL('./spotify-recent.svg', import.meta.url), 'utf8');

// Tiny images, each the base64 of a real file of its type (2x2 JPEG, WebP and PNG, a 1x1 GIF).
export const RASTERS = {
  jpeg:
    '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAA0JCgsKCA0LCgsODg0PEyAVExISEyccHhcgLikxMC4pLSwzOko+MzZGNywtQFdBRkxOUlNSMj5aYVpQYEpRUk' +
    '//2wBDAQ4ODhMREyYVFSZPNS01T09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT0//wAARCAACAAIDASIAAhEBAxEB/8QAFQABAQ' +
    'AAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAABQb/xAAYEQADAQEAAAAAAAAAAAAAAAAAAQIxMv/aAAwDAQACEQMRAD' +
    '8AlgD61lLHKP/Z',
  webp: 'UklGRjIAAABXRUJQVlA4ICYAAABwAQCdASoCAAIAAoBCJaACdAFAAAD+645YwmknR/qv8fftglAAAA==',
  png: 'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAGElEQVR4AWLSbNj5/4Cl9n+m6TuLGEAAAAAA//8LmEIFAAAABklEQVQDAEh4BksFdB3KAAAAAElFTkSuQmCC',
  gif: 'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7',
};

// A made-up Apple Music uid, shaped like the real ones.
export const APPLE_UID = '000000.0123456789abcdef0123456789abcdef.0000';

// The cover as Apple Music's service sends it: JPEG bytes labelled WebP.
export const APPLE_COVER = `data:image/webp;base64,${RASTERS.jpeg}`;

// A stand-in for the Apple Music service's card, written here to its outline alone: the facts the relay
// reads from it (h1.song-title, h2.song-artist, img.cover-image) wrapped in a foreignObject, with markup
// and a style of the stand-in's own that the relay must never pass on. None of the service's own markup,
// style or artwork is copied. The song, artist and cover are inserted verbatim.
export function appleSvg({ song = 'Bleu Nuit', artist = 'Hélène &amp; Les Ondes', cover = APPLE_COVER, extra = '' } = {}) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="345" height="534"><foreignObject width="343" height="534">` +
    '<style>.upstream-style{color:#123456}</style>' +
    '<div xmlns="http://www.w3.org/1999/xhtml" class="container upstream-style">' +
    '<div class="upstream-header">UPSTREAM-HEADER</div>' +
    `<div><img class="cover-image" src="${cover}"/></div>` +
    `<div><h1 class="song-title upstream-style">${song}</h1><h2 class="upstream-style song-artist">${artist}</h2></div>` +
    `<p class="upstream-only">UPSTREAM-ONLY</p>${extra}</div></foreignObject></svg>`;
}

// The shape of the service's error card, which it sends with status 200: a bug icon, a "Failure!" heading
// and a message.
export function appleErrorSvg(message = 'User does not exist') {
  return '<svg xmlns="http://www.w3.org/2000/svg" width="345" height="534"><foreignObject width="343" height="534">' +
    '<div xmlns="http://www.w3.org/1999/xhtml" class="container">' +
    '<svg xmlns="http://www.w3.org/2000/svg" class="bug-icon" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/></svg>' +
    `<h1>Failure!</h1><p>${message}</p></div></foreignObject></svg>`;
}

export const PALETTE = {
  light: { bg: '#fbf8f5', text: '#2a1f1a', muted: '#6b5e52', line: '#d8cfc1' },
  dark: { bg: '#1e1315', text: '#f8f3e9', muted: '#b6aea7', line: '#50343c' },
};

export function cardsJson({ palette = PALETTE, uid = '1joahg6umn39flaqsl1c3j9n3', ...rest } = {}) {
  return JSON.stringify({ generated: '2026-09-26T07:38Z', commits: 1920, palette, spotify: { uid }, ...rest });
}

// coderprint.json as the generator writes it: the figures, and what the relay reads under presentation.
export function coderprintJson({ palette = PALETTE, uid = '1joahg6umn39flaqsl1c3j9n3', ...rest } = {}) {
  return JSON.stringify({
    schema: 'coderprint/1',
    as_of: '2026-09-27',
    quantity: { in_use_loc: { value: 410216, unit: 'lines of code', provenance: 'measured' } },
    presentation: { theme: 'sage', palette, spotify: { uid }, ...rest },
  });
}

// cards.json as the generator writes it for Apple Music: the uid under apple_music, and no Spotify.
export function appleCardsJson({ palette = PALETTE, uid = APPLE_UID } = {}) {
  return JSON.stringify({ generated: '2026-09-26T07:38Z', commits: 1920, palette, apple_music: { uid } });
}
