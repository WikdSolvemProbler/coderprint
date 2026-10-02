import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { readFileSync } from 'node:fs';

import { buildCard, buildCompactCard, nowPlaying, readCompactPanel, svgInner } from '../lib/compose.js';
import { PALETTE, PANEL_SVG, PIXEL, RASTERS, appleSvg, compactPanelSvg, spotifySvg, withoutVinylTexture } from './fixtures.js';
import { VINYL_TEXTURE } from '../lib/vinyl-texture.js';

const providers = {
  spotify: (options = {}) => spotifySvg({ artist: 'Shared Artist', song: 'Shared Song', cover: PIXEL, ...options }),
  apple: (options = {}) => appleSvg({ artist: 'Shared Artist', song: 'Shared Song', cover: PIXEL, ...options }),
};

function render(service, layout, music = providers[service](), palette = PALETTE.light, extra = '') {
  const options = { service, glow: palette === PALETTE.dark };
  return layout === 'wide'
    ? buildCard(PANEL_SVG.replace('</svg>', `${extra}</svg>`), music, palette, options)
    : buildCompactCard(readCompactPanel(compactPanelSvg({ extra })), music, palette, options);
}

function record(card) {
  return card.match(/<svg x="[\d.]+" y="[\d.]+" width="[\d.]+" height="[\d.]+" viewBox="0 0 100 100"[^>]*>[\s\S]*?<\/svg>/)?.[0];
}

function styles(card) {
  return [...card.matchAll(/<style>([^<]*)<\/style>/g)].map(([, css]) => css).join('\n');
}

function withoutMotion(css) {
  let result = css;
  const start = /@media\s*\(prefers-reduced-motion:\s*no-preference\)\s*\{/;
  for (let match = start.exec(result); match; match = start.exec(result)) {
    let end = match.index + match[0].length;
    let depth = 1;
    while (depth && end < result.length) {
      if (result[end] === '{') depth += 1;
      if (result[end] === '}') depth -= 1;
      end += 1;
    }
    assert.equal(depth, 0, 'the motion media query is well formed');
    result = result.slice(0, match.index) + result.slice(end);
  }
  return result;
}

describe('the shared native vinyl artwork', () => {
  it('embeds the exact committed WebP texture without an additional image request', () => {
    const bytes = readFileSync(new URL('../assets/vinyl/record-ridges.webp', import.meta.url));
    assert.equal(bytes.subarray(0, 4).toString(), 'RIFF');
    assert.equal(bytes.subarray(8, 12).toString(), 'WEBP');
    assert.equal(VINYL_TEXTURE, `data:image/webp;base64,${bytes.toString('base64')}`);
  });

  it('draws the same grooved record and circular album label for both providers in both slots', () => {
    for (const layout of ['wide', 'compact']) {
      const spotify = render('spotify', layout);
      const apple = render('apple', layout);
      assert.notEqual(svgInner(spotify), null);
      assert.notEqual(svgInner(apple), null);
      const vinyl = record(spotify);
      assert.ok(vinyl, `${layout} has a record`);
      assert.equal(record(apple), vinyl, `${layout} shares the same artwork renderer`);
      assert.match(vinyl, /class="relay-vinyl-record"/);
      assert.match(vinyl, /<clipPath id="relay-vinyl-label"><circle cx="50" cy="50" r="27"\/><\/clipPath>/);
      assert.match(vinyl, /<image x="23" y="23" width="54" height="54"[^>]*clip-path="url\(#relay-vinyl-label\)"/);
      assert.ok(vinyl.includes(`href="${PIXEL}"`));
      assert.ok(vinyl.includes('id="relay-vinyl-texture"') && vinyl.includes(`href="${VINYL_TEXTURE}"`));
      assert.ok(vinyl.includes('id="relay-vinyl-disc"') && vinyl.includes('clip-path="url(#relay-vinyl-disc)"'));
      const slot = layout === 'wide' ? ['10', '131', '300'] : ['14', '14', '84'];
      assert.ok(vinyl.startsWith(`<svg x="${slot[0]}" y="${slot[1]}" width="${slot[2]}" height="${slot[2]}" viewBox="0 0 100 100"`));
      assert.match(spotify, layout === 'wide' ? /width="896" height="445"/ : /width="360" height="774"/);
      assert.doesNotMatch(spotify + apple, /foreignObject|<div|<script|<animate|<set\b|onload=|onerror=/i);
    }
  });

  it('keeps the complete record visible at rest and opts into spinning only when motion is allowed', () => {
    for (const service of Object.keys(providers)) {
      for (const layout of ['wide', 'compact']) {
        const card = render(service, layout, providers[service](), PALETTE.dark);
        const css = styles(card);
        assert.match(css, /@media\s*\(prefers-reduced-motion:\s*no-preference\)\{/);
        assert.match(css, /@keyframes relay-vinyl-spin\{/);
        assert.match(css, /animation:relay-vinyl-spin [^;}]*linear infinite/);
        assert.match(css, /@keyframes relay-vinyl-glint\{/);
        assert.match(css, /animation:relay-vinyl-glint [^;}]*ease-in-out infinite/);
        const still = withoutMotion(css);
        assert.doesNotMatch(still, /vinyl-spin|vinyl-glint|animation(?:-name)?\s*:/, 'reduced motion and CSS-disabled viewers see a static record');
        const vinyl = record(card);
        assert.doesNotMatch(vinyl.replace(/<style>[\s\S]*?<\/style>/g, ''), /\sopacity="0"|\svisibility="hidden"|\sdisplay="none"|<animate|<script/i);
        assert.ok(vinyl.includes(`href="${PIXEL}"`), 'the artwork is in the SVG rather than generated by animation');
      }
    }
  });

  it('preserves playing, recently played and last-played statuses while animating available tracks', () => {
    for (const layout of ['wide', 'compact']) {
      for (const status of ['Now playing on', 'Recently played on']) {
        const card = render('spotify', layout, providers.spotify({ status }));
        assert.ok(card.includes(`>${status}</text>`));
        assert.match(card, /relay-vinyl-record|relay-vinyl-spin/);
        if (status.startsWith('Recently')) assert.doesNotMatch(card, />Now playing on<\/text>/);
      }
      const apple = render('apple', layout);
      assert.ok(apple.includes('>Last played on Apple Music</text>'));
      assert.doesNotMatch(apple, />Now playing on<\/text>|>Recently played on<\/text>/);
      assert.match(apple, /relay-vinyl-record|relay-vinyl-spin/);
    }
  });

  it('shows the placeholder without a spinning record when there is no track', () => {
    for (const service of Object.keys(providers)) {
      for (const layout of ['wide', 'compact']) {
        for (const music of [null, '', providers[service]({ artist: '', song: '' })]) {
          const card = render(service, layout, music);
          assert.notEqual(svgInner(card), null);
          assert.match(card, />Nothing playing<\/text>/);
          assert.doesNotMatch(card, /vinyl-record|vinyl-spin|vinyl-label|vinyl-sheen|<image /);
        }
      }
    }
  });

  it('retains track text and the record when artwork is missing or hostile, without embedding it', () => {
    const covers = ['', 'https://outside.example/art.png', 'javascript:alert(1)', 'data:image/svg+xml;base64,PHN2Zy8+',
      'data:image/png;base64,AAAA', 'data:image/jpeg;base64,not-base64!', 'data:image/png;base64,AA&quot;/&gt;&lt;script'];
    for (const service of Object.keys(providers)) {
      for (const layout of ['wide', 'compact']) {
        for (const cover of covers) {
          const card = render(service, layout, providers[service]({ cover, logo: cover }));
          assert.notEqual(svgInner(card), null);
          assert.ok(card.includes('>Shared Artist</text>') && card.includes('>Shared Song</text>'), `${service} ${layout}`);
          assert.match(record(card), /class="relay-vinyl-record"/);
          assert.doesNotMatch(withoutVinylTexture(record(card)), /<image /);
          assert.doesNotMatch(withoutVinylTexture(card), /outside\.example|javascript:|not-base64|<script|<image /i);
        }
      }
    }
  });

  it('uses detected raster bytes for both providers and never forwards upstream styles or layout', () => {
    for (const service of Object.keys(providers)) {
      const music = providers[service]({ cover: `data:image/webp;base64,${RASTERS.jpeg}`,
        extra: '<style>.hostile-upstream{animation:unexpected 1ms infinite;fill:#abcdef}</style><g id="upstream-layout"/>' });
      const facts = nowPlaying(svgInner(music), service);
      assert.equal(facts.cover, `data:image/jpeg;base64,${RASTERS.jpeg}`);
      for (const layout of ['wide', 'compact']) {
        const card = render(service, layout, music);
        assert.ok(record(card).includes(`href="data:image/jpeg;base64,${RASTERS.jpeg}"`));
        assert.doesNotMatch(withoutVinylTexture(card), /image\/webp|hostile-upstream|unexpected|#abcdef|upstream-layout|upstream-style|foreignObject|<div/);
      }
    }
  });

  it('keeps every generated identifier and spin keyframe clear of panel collisions', () => {
    const extra = '<g id="relay-vinyl-label"/><g id="&#114;elay1-vinyl-texture"/><g id="relay2-vinyl-record"/>';
    for (const service of Object.keys(providers)) {
      for (const layout of ['wide', 'compact']) {
        const card = render(service, layout, providers[service](), PALETTE.dark, extra);
        const vinyl = record(card);
        assert.match(vinyl, /class="relay3-vinyl-record"/);
        assert.match(vinyl, /id="relay3-vinyl-label"/);
        assert.match(vinyl, /url\(#relay3-vinyl-label\)/);
        assert.match(vinyl, /id="relay3-vinyl-texture"/);
        assert.match(vinyl, /id="relay3-vinyl-disc"/);
        assert.match(styles(card), /@keyframes relay3-vinyl-spin\{/);
        assert.match(styles(card), /@keyframes relay3-vinyl-glint\{/);
        assert.doesNotMatch(styles(card), /@keyframes relay(?:1|2)?-vinyl-(?:spin|glint)\{/);
        const ids = [...card.matchAll(/\bid="([^"]+)"/g)].map(([, id]) => id.replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n))));
        assert.equal(new Set(ids).size, ids.length, 'no duplicate IDs');
        for (const [, id] of card.matchAll(/url\(#([^)]*)\)/g)) assert.ok(ids.includes(id), `resolved reference ${id}`);
      }
    }
  });
});
