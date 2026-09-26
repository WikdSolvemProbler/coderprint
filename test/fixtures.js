// Small stand-ins for the two upstream documents, shaped like the real ones.

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

// The artist and song are inserted verbatim, so a test can pass markup the upstream failed to escape.
export function spotifySvg({ artist = 'Mura Masa', song = 'Love$ick (feat. A$AP Rocky)', extra = '' } = {}) {
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
        <div class="playing">Now playing on <img class="logo" src="${PIXEL}" /></div>
        <div class="artist">${artist}</div>
        <div class="song">${song}</div>
        <div id='bars'><div class='bar'></div><div class='bar'></div><div class='bar'></div></div>
        ${extra}
          <a href="{}" target="_BLANK">
            <center>
              <img src="${PIXEL}" width="300" height="300" class="cover" />
            </center>
          </a>
    </div>
  </foreignObject>
</svg>`;
}

export const PALETTE = {
  light: { bg: '#fbf8f5', text: '#2a1f1a', muted: '#6b5e52', line: '#d8cfc1' },
  dark: { bg: '#1e1315', text: '#f8f3e9', muted: '#b6aea7', line: '#50343c' },
};

export function cardsJson({ palette = PALETTE, uid = '1joahg6umn39flaqsl1c3j9n3', ...rest } = {}) {
  return JSON.stringify({ generated: '2026-09-26T07:38Z', commits: 1920, palette, spotify: { uid }, ...rest });
}
