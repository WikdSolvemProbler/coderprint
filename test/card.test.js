import assert from 'node:assert/strict';
import { afterEach, beforeEach, describe, it } from 'node:test';

import handler from '../api/card.js';
import { BAR_RULES, DEFAULT_PALETTES, GLOW_RULES, appleUrl, spotifyUrl, svgInner } from '../lib/compose.js';
import {
  APPLE_UID,
  COMPACT_PANEL_SVG,
  PALETTE,
  PANEL_SVG,
  PIXEL,
  RASTERS,
  RECENT_SVG,
  appleCardsJson,
  appleErrorSvg,
  appleSvg,
  cardsJson,
  compactPanelSvg,
  spotifySvg,
} from './fixtures.js';

const USER = 'WikdSolvemProbler';
const UID = '1joahg6umn39flaqsl1c3j9n3';
const RAW = `https://raw.githubusercontent.com/${USER}/${USER}/HEAD/assets/`;
const SPOTIFY = 'https://spotify-github-profile.kittinanx.com/api/view?';
const APPLE = 'https://music-profile.rayriffy.com/';
const CARD_CACHE = 'public, max-age=0, s-maxage=10, stale-while-revalidate=86400, stale-if-error=86400';
const MB = 1024 * 1024;

const realFetch = globalThis.fetch;
const realUsers = process.env.CODERPRINT_USERS;
let calls;

// Stands in for the upstreams, routing each request by what it asks for.
function upstream({
  cards = () => ok(cardsJson()),
  panel = () => ok(PANEL_SVG),
  compact = () => ok(COMPACT_PANEL_SVG),
  spotify = () => ok(spotifySvg()),
  apple = () => ok(appleSvg()),
} = {}) {
  calls = [];
  globalThis.fetch = async (url, options) => {
    const href = String(url);
    calls.push({ href, options });
    if (href === `${RAW}cards.json`) return cards(options);
    if (href.startsWith(`${RAW}panel-compact-`)) return compact(options);
    if (href.startsWith(`${RAW}panel-`)) return panel(options);
    if (href.startsWith(SPOTIFY)) return spotify(options);
    if (href.startsWith(APPLE)) return apple(options);
    throw new TypeError(`unexpected fetch of ${href}`);
  };
}

function ok(body, headers) {
  return new Response(body, { status: 200, headers });
}

function statusOnly(code) {
  return () => new Response('upstream says no', { status: code });
}

function networkError() {
  throw new TypeError('fetch failed');
}

// A real hung upstream holds a socket open, which keeps the process alive. The relay's deadline
// timer does not, so each stand-in below holds a timer of its own until it is abandoned.
function holdOpen() {
  return setTimeout(() => {}, 60_000);
}

// An upstream that never answers; like real fetch, it gives up only when the signal aborts.
function hang(options) {
  const socket = holdOpen();
  return new Promise((_, reject) => {
    options.signal.addEventListener(
      'abort',
      () => {
        clearTimeout(socket);
        reject(options.signal.reason);
      },
      { once: true },
    );
  });
}

// An upstream that answers after ms, as respond() would, unless the signal aborts first.
function delayed(ms, respond) {
  return (options) => {
    const socket = holdOpen();
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        clearTimeout(socket);
        resolve(respond(options));
      }, ms);
      options.signal.addEventListener(
        'abort',
        () => {
          clearTimeout(timer);
          clearTimeout(socket);
          reject(options.signal.reason);
        },
        { once: true },
      );
    });
  };
}

// Headers and a first chunk arrive, then nothing, and the stream ignores the abort signal.
function stall() {
  const socket = holdOpen();
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode('<svg xmlns="http://www.w3.org/2000/svg">'));
    },
    cancel() {
      clearTimeout(socket);
    },
  });
  return new Response(body, { status: 200 });
}

// A body of the given size, produced on demand, recording how many bytes were actually pulled.
function huge(bytes, headers) {
  const chunk = new Uint8Array(64 * 1024).fill(0x20);
  const meter = { served: 0 };
  const body = new ReadableStream({
    pull(controller) {
      if (meter.served >= bytes) return controller.close();
      meter.served += chunk.byteLength;
      controller.enqueue(chunk.slice());
    },
  });
  return { respond: () => new Response(body, { status: 200, headers }), meter };
}

function get(query, method = 'GET') {
  return handler.fetch(new Request(`https://coderprint.test/api/card?${query}`, { method }));
}

async function expectFailure(response, status) {
  assert.equal(response.status, status);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.equal(response.headers.get('content-type'), 'text/plain; charset=utf-8');
  const text = await response.text();
  assert.ok(text.length > 0 && text.length < 200, text);
  return text;
}

async function expectCard(response) {
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('content-type'), 'image/svg+xml; charset=utf-8');
  assert.equal(response.headers.get('cache-control'), CARD_CACHE);
  const svg = await response.text();
  assert.notEqual(svgInner(svg), null, 'the card must be a well formed SVG');
  assert.match(svg, /^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg"[^>]* width="896" height="445"/);
  assert.doesNotMatch(svg, /<script|\son\w+\s*=|evil\.example/i);
  return svg;
}

// The compact card over the fixture's 662-unit panel: 360 wide, the panel and the 112-unit strip tall.
async function expectCompactCard(response) {
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('content-type'), 'image/svg+xml; charset=utf-8');
  assert.equal(response.headers.get('cache-control'), CARD_CACHE);
  const svg = await response.text();
  assert.notEqual(svgInner(svg), null, 'the card must be a well formed SVG');
  assert.match(svg, /^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg"[^>]* width="360" height="774"/);
  assert.doesNotMatch(svg, /<script|\son\w+\s*=|evil\.example|<foreignObject/i);
  return svg;
}

const COMPACT = `user=${USER}&mode=dark&layout=compact`;

async function timed(run) {
  const start = performance.now();
  const result = await run();
  return { result, ms: performance.now() - start };
}

beforeEach(() => {
  process.env.CODERPRINT_USERS = USER;
  upstream();
});

afterEach(() => {
  globalThis.fetch = realFetch;
  if (realUsers === undefined) delete process.env.CODERPRINT_USERS;
  else process.env.CODERPRINT_USERS = realUsers;
});

describe('input', () => {
  it('answers 400 to anything but one valid login and one valid mode, without fetching', async () => {
    const bad = [
      '',
      'mode=dark',
      `user=${USER}`,
      `user=${USER}&mode=Dark`,
      `user=${USER}&mode=auto`,
      `user=${USER}&mode=dark&mode=light`,
      `user=${USER}&user=other&mode=dark`,
      'user=-bad&mode=dark',
      'user=bad-&mode=dark',
      'user=a--b&mode=dark',
      `user=${'x'.repeat(40)}&mode=dark`,
      'user=..%2F..%2Fx&mode=dark',
      'user=a%2Fb&mode=dark',
      'user=%3Cscript%3E&mode=dark',
      'user=&mode=dark',
    ];
    for (const query of bad) await expectFailure(await get(query), 400);
    assert.equal(calls.length, 0);
  });

  it('answers 403 to a user who is not on the list, without fetching', async () => {
    await expectFailure(await get('user=someone&mode=dark'), 403);
    for (const list of [undefined, '', ' , ']) {
      if (list === undefined) delete process.env.CODERPRINT_USERS;
      else process.env.CODERPRINT_USERS = list;
      await expectFailure(await get(`user=${USER}&mode=dark`), 403);
    }
    assert.equal(calls.length, 0);
  });

  it('matches the allow list case-insensitively', async () => {
    process.env.CODERPRINT_USERS = ' someone , wikdsolvemprobler ';
    await expectCard(await get(`user=${USER}&mode=dark`));
  });

  it('answers HEAD like GET without a body and refuses other methods', async () => {
    const head = await get(`user=${USER}&mode=dark`, 'HEAD');
    assert.equal(head.status, 200);
    assert.equal(head.headers.get('cache-control'), CARD_CACHE);
    assert.equal(await head.text(), '');
    const post = await get(`user=${USER}&mode=dark`, 'POST');
    await expectFailure(post, 405);
    assert.equal(post.headers.get('allow'), 'GET, HEAD');
  });
});

describe('the card', () => {
  it('merges the panel and the recolored live Spotify card', async () => {
    const svg = await expectCard(await get(`user=${USER}&mode=dark`));
    assert.ok(svg.includes(`<rect width="896" height="445" rx="10" fill="${PALETTE.dark.bg}"/>`));
    assert.ok(svg.includes(`stroke="${PALETTE.dark.line}"`));
    assert.ok(svg.includes(`.artist{color:${PALETTE.dark.text}!important}.song{color:${PALETTE.dark.muted}!important}${BAR_RULES}${GLOW_RULES}</style>`));
    assert.ok(svg.includes('fill="url(#vignetteRight)"'));
    assert.ok(svg.includes('<div class="artist">Mura Masa</div>'));
    assert.doesNotMatch(svg, /Nothing playing/);
  });

  it('glows only in dark mode', async () => {
    const svg = await expectCard(await get(`user=${USER}&mode=light`));
    assert.ok(svg.includes(`${BAR_RULES}</style>`));
    assert.ok(!svg.includes(GLOW_RULES) && !svg.includes('vignetteRight'));
  });

  it('fetches from the HEAD ref and the widget, refusing redirects, each under a deadline', async () => {
    await get(`user=${USER}&mode=light`);
    assert.deepEqual(calls.map((call) => call.href).sort(), [
      `${RAW}cards.json`,
      `${RAW}panel-light.svg`,
      spotifyUrl(UID, PALETTE.light.bg),
    ]);
    for (const { options } of calls) {
      assert.equal(options.redirect, 'error');
      assert.ok(options.signal instanceof AbortSignal);
    }
  });

  it('sends security headers with the image', async () => {
    for (const query of [`user=${USER}&mode=dark`, COMPACT]) {
      const response = await get(query);
      assert.match(response.headers.get('content-security-policy'), /default-src 'none'/);
      assert.match(response.headers.get('content-security-policy'), /; sandbox$/);
      assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
    }
  });

  it('drops a widget meta refresh from the wide and the compact card, and a panel one from the compact card', async () => {
    const refresh = '<meta http-equiv="refresh" content="1;url=https://evil.example/leak-widget-meta-refresh"/>';
    upstream({ spotify: () => ok(spotifySvg({ extra: refresh })) });
    const wide = await expectCard(await get(`user=${USER}&mode=dark`));
    assert.doesNotMatch(wide, /<meta|http-equiv|refresh/i);
    assert.ok(wide.includes('<div class="artist">Mura Masa</div>'));
    const compact = await expectCompactCard(await get(COMPACT));
    assert.doesNotMatch(compact, /<meta|http-equiv|refresh/i);
    const htmlRefresh = refresh.replace('<meta ', '<h:meta xmlns:h="http://www.w3.org/1999/xhtml" ');
    upstream({ compact: () => ok(compactPanelSvg({ extra: htmlRefresh })) });
    const panel = await expectCompactCard(await get(COMPACT));
    assert.doesNotMatch(panel, /meta|http-equiv|refresh/i);
    assert.ok(panel.includes('<circle class="now"'));
  });

  it('bounces the equalizer of a recently played track in the wide and the compact card', async () => {
    upstream({ spotify: () => ok(RECENT_SVG) });
    const wide = await expectCard(await get(`user=${USER}&mode=dark`));
    assert.equal(wide.split('<div class="bar"></div>').length - 1, 75);
    assert.match(wide, /<div class="playing">Recently played on </);
    const compact = await expectCompactCard(await get(COMPACT));
    assert.match(compact, />Recently played on<\/text>/);
    assert.ok(compact.includes('animation:relay-bounce 425ms linear infinite alternate'));
    assert.equal(compact.split('class="relay-bar"').length - 1, 47);
  });

  it('shows the placeholder without asking Spotify when there is no usable uid', async () => {
    const bodies = [JSON.stringify({ palette: PALETTE }), ...[null, '', 'abc&evil=1', 'a'.repeat(65), 42].map((uid) => cardsJson({ uid }))];
    for (const body of bodies) {
      upstream({ cards: () => ok(body) });
      const svg = await expectCard(await get(`user=${USER}&mode=dark`));
      assert.match(svg, /Nothing playing/);
      assert.ok(calls.every((call) => !call.href.startsWith(SPOTIFY)));
    }
  });

  it('uses the default palette when cards.json carries a hostile color', async () => {
    const palette = { dark: { ...PALETTE.dark, bg: 'red;}' }, light: PALETTE.light };
    upstream({ cards: () => ok(cardsJson({ palette })) });
    const svg = await expectCard(await get(`user=${USER}&mode=dark`));
    assert.ok(!svg.includes('red;}'));
    assert.ok(svg.includes(`fill="${DEFAULT_PALETTES.dark.bg}"`));
    assert.ok(calls.some((call) => call.href === spotifyUrl(UID, DEFAULT_PALETTES.dark.bg)));
  });

  it('keeps an escaped song title as text and strips what cannot run in an image', async () => {
    const song = '&lt;/style&gt;&lt;script&gt;alert(1)&lt;/script&gt;';
    const extra = '<script>alert(2)</script><img src="https://evil.example/t.png" onerror="alert(3)"/>';
    upstream({ spotify: () => ok(spotifySvg({ song, extra })) });
    const svg = await expectCard(await get(`user=${USER}&mode=dark`));
    assert.ok(svg.includes(`<div class="song">${song}</div>`));
    assert.doesNotMatch(svg, /Nothing playing|alert\(2\)/);
  });

  it('shows the placeholder when the Spotify card is unusable', async () => {
    const big = huge(10 * MB);
    const unusable = {
      'a 500': statusOnly(500),
      'a 404': statusOnly(404),
      'an HTML page': () => ok('<!doctype html><html><body>Bad gateway</body></html>'),
      'a JSON error': () => ok('{"error":"rate limited"}'),
      'an empty body': () => ok(''),
      'a network error': networkError,
      'an unescaped closing style tag in the song title': () => ok(spotifySvg({ song: '</style><script>alert(1)</script>' })),
      'an unescaped ampersand': () => ok(spotifySvg({ song: 'Rock & Roll' })),
      'a 10 MB body': big.respond,
    };
    for (const [label, spotify] of Object.entries(unusable)) {
      upstream({ spotify });
      const svg = await expectCard(await get(`user=${USER}&mode=light`));
      assert.match(svg, /Nothing playing/, label);
      assert.ok(svg.includes(`fill="${PALETTE.light.muted}"`), label);
    }
    assert.ok(big.meter.served < 3 * MB, `pulled ${big.meter.served} bytes`);
  });
});

describe('upstream failures', () => {
  it('answers 502 when cards.json is unavailable or not a JSON object', async () => {
    const big = huge(10 * MB);
    const failures = {
      'a 404': statusOnly(404),
      'a network error': networkError,
      'not JSON': () => ok('<html>not json</html>'),
      'a JSON array': () => ok('[1, 2]'),
      'a 10 MB body': big.respond,
    };
    for (const [label, cards] of Object.entries(failures)) {
      upstream({ cards });
      const text = await expectFailure(await get(`user=${USER}&mode=dark`), 502);
      assert.match(text, /cards\.json/, label);
      assert.ok(calls.every((call) => !call.href.startsWith(SPOTIFY)), label);
    }
    assert.ok(big.meter.served < 1 * MB, `pulled ${big.meter.served} bytes`);
  });

  it('answers 502 when the panel is unavailable or not an SVG document', async () => {
    const big = huge(10 * MB);
    const declared = huge(10 * MB, { 'content-length': String(10 * MB) });
    const failures = {
      'a 404': statusOnly(404),
      'a network error': networkError,
      'an HTML page': () => ok('<html><body><svg></svg></body></html>'),
      'no root svg': () => ok('<g xmlns="http://www.w3.org/2000/svg"><rect/></g>'),
      'a truncated document': () => ok(PANEL_SVG.slice(0, 600)),
      'a 10 MB body': big.respond,
      'a declared 10 MB body': declared.respond,
    };
    for (const [label, panel] of Object.entries(failures)) {
      upstream({ panel });
      const text = await expectFailure(await get(`user=${USER}&mode=dark`), 502);
      assert.match(text, /panel-dark\.svg/, label);
    }
    assert.ok(big.meter.served < 3 * MB, `pulled ${big.meter.served} bytes`);
    assert.ok(declared.meter.served <= 64 * 1024, `pulled ${declared.meter.served} bytes`);
  });
});

describe('deadlines', () => {
  it('gives up on a cards.json that never answers and answers 502', async () => {
    upstream({ cards: hang });
    const { result, ms } = await timed(() => get(`user=${USER}&mode=dark`));
    await expectFailure(result, 502);
    assert.ok(ms > 2500 && ms < 5000, `${ms} ms`);
  });

  it('gives up on a panel whose body stalls and answers 502', async () => {
    upstream({ panel: stall });
    const { result, ms } = await timed(() => get(`user=${USER}&mode=dark`));
    await expectFailure(result, 502);
    assert.ok(ms > 2500 && ms < 5000, `${ms} ms`);
  });

  it('shows the placeholder when Spotify never answers or stalls mid-body', async () => {
    for (const spotify of [hang, stall]) {
      upstream({ spotify });
      const { result, ms } = await timed(() => get(`user=${USER}&mode=dark`));
      assert.match(await expectCard(result), /Nothing playing/);
      assert.ok(ms > 2000 && ms < 4500, `${ms} ms`);
    }
  });
});

describe('the compact card', () => {
  it('answers 400 to a layout other than compact, without fetching', async () => {
    const bad = ['', 'wide', 'Compact', 'COMPACT', 'compact%20', 'compact%00', 'tall', 'compact&layout=compact', 'compact&layout=wide'];
    for (const layout of bad) {
      const text = await expectFailure(await get(`user=${USER}&mode=dark&layout=${layout}`), 400);
      assert.match(text, /layout=compact/, layout);
    }
    await expectFailure(await get('user=-bad&mode=dark&layout=compact'), 400);
    await expectFailure(await get(`user=${USER}&mode=auto&layout=compact`), 400);
    assert.equal(calls.length, 0);
  });

  it('answers 403 to a user who is not on the list, without fetching', async () => {
    await expectFailure(await get('user=someone&mode=dark&layout=compact'), 403);
    assert.equal(calls.length, 0);
  });

  it('draws the compact panel over a native Spotify strip, without fetching the wide panel', async () => {
    const svg = await expectCompactCard(await get(`user=${USER}&mode=light&layout=compact`));
    assert.deepEqual(calls.map((call) => call.href).sort(), [
      `${RAW}cards.json`,
      `${RAW}panel-compact-light.svg`,
      spotifyUrl(UID, PALETTE.light.bg),
    ]);
    for (const { options } of calls) {
      assert.equal(options.redirect, 'error');
      assert.ok(options.signal instanceof AbortSignal);
    }
    assert.ok(svg.includes(`<rect width="360" height="774" rx="10" fill="${PALETTE.light.bg}"/>`));
    assert.ok(svg.includes('<svg x="0" y="0" width="360" height="662" viewBox="0 0 360 662">'));
    assert.ok(svg.includes(`stroke="${PALETTE.light.line}"`));
    assert.match(svg, new RegExp(`fill="${PALETTE.light.text}">Mura Masa</text>`));
    assert.match(svg, new RegExp(`fill="${PALETTE.light.muted}">Love\\$ick \\(feat\\. A\\$AP Rocky\\)</text>`));
    assert.ok(svg.includes(`href="${PIXEL}"`));
    assert.doesNotMatch(svg, /Nothing playing|<div/);
  });

  it('answers HEAD like GET without a body', async () => {
    const head = await get(COMPACT, 'HEAD');
    assert.equal(head.status, 200);
    assert.equal(head.headers.get('content-type'), 'image/svg+xml; charset=utf-8');
    assert.equal(await head.text(), '');
  });

  it('glows only in dark mode, with the same vignette as the wide card', async () => {
    const dark = await expectCompactCard(await get(COMPACT));
    for (const name of ['playing', 'artist', 'bars']) {
      assert.ok(dark.includes(`<filter id="relay-glow-${name}"`), name);
      assert.ok(dark.includes(`filter="url(#relay-glow-${name})"`), name);
    }
    assert.ok(dark.includes('fill="url(#relay-vignette)"'));
    const light = await expectCompactCard(await get(`user=${USER}&mode=light&layout=compact`));
    assert.doesNotMatch(light, /<filter|filter=|vignette/);
  });

  it('runs the compact panel through the sanitizer', async () => {
    const extra =
      '<script>alert(1)</script><rect onload="alert(2)" width="1" height="1"/>' +
      '<image href="https://evil.example/x.png"/><a href="javascript:alert(3)"><text>x</text></a>';
    upstream({ compact: () => ok(compactPanelSvg({ extra })) });
    const svg = await expectCompactCard(await get(COMPACT));
    assert.doesNotMatch(svg, /alert|javascript/);
    assert.ok(svg.includes('<rect width="1" height="1"/>'));
  });

  it('escapes a hostile artist and song and keeps them as text', async () => {
    const artist = '&lt;/text&gt;&lt;script&gt;';
    const song = '&lt;/text&gt;&lt;/svg&gt; &amp; ]]&gt; &quot;';
    upstream({ spotify: () => ok(spotifySvg({ artist, song })) });
    const svg = await expectCompactCard(await get(COMPACT));
    assert.ok(svg.includes(`filter="url(#relay-glow-artist)">${artist}</text>`));
    assert.ok(svg.includes(`fill="${PALETTE.dark.muted}">&lt;/text&gt;&lt;/svg&gt; &amp; ]]&gt; "</text>`));
    assert.doesNotMatch(svg, /\]\]>/);
  });

  it('draws only data: rasters as the cover and logo', async () => {
    for (const url of ['https://evil.example/c.png', '#grid', 'data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=', 'data:text/html,x', '']) {
      upstream({ spotify: () => ok(spotifySvg({ cover: url, logo: url })) });
      const svg = await expectCompactCard(await get(COMPACT));
      assert.doesNotMatch(svg, /<image[^>]*href="(?!data:image\/png;base64,)/, url);
      assert.ok(!svg.includes('clip-path="url(#relay-cover)"'), url);
      assert.ok(svg.includes('>Mura Masa</text>'), url);
    }
  });

  it('says nothing is playing when there is no uid or Spotify fails', async () => {
    const cases = [
      { cards: () => ok(cardsJson({ uid: null })) },
      { spotify: statusOnly(500) },
      { spotify: () => ok('{"error":"rate limited"}') },
      { spotify: () => ok(spotifySvg({ artist: '  ' })) },
      { spotify: () => ok(spotifySvg({ song: 'Rock & Roll' })) },
    ];
    for (const routes of cases) {
      upstream(routes);
      const svg = await expectCompactCard(await get(COMPACT));
      assert.match(svg, /Nothing playing/);
      assert.ok(svg.includes(`fill="${PALETTE.dark.muted}"`));
      assert.doesNotMatch(svg, /relay-glow/);
    }
  });

  it('falls back to the wide card when the compact panel is missing or unusable', async () => {
    const big = huge(10 * MB);
    const unusable = {
      'a 404': statusOnly(404),
      'a network error': networkError,
      'an HTML page': () => ok('<html><body><svg></svg></body></html>'),
      'a truncated document': () => ok(COMPACT_PANEL_SVG.slice(0, 600)),
      'the wide width': () => ok(compactPanelSvg({ width: '576' })),
      'a width with a unit': () => ok(compactPanelSvg({ width: '360px' })),
      'a height under 400': () => ok(compactPanelSvg({ height: '399' })),
      'a height over 900': () => ok(compactPanelSvg({ height: '901' })),
      'no height': () => ok(COMPACT_PANEL_SVG.replace(' height="662"', '')),
      'a viewBox of another size': () => ok(compactPanelSvg({ viewBox: '0 0 576 445' })),
      'markup that is not well formed': () => ok(compactPanelSvg({ extra: '<text>a < b</text>' })),
      'a 10 MB body': big.respond,
    };
    for (const [label, compact] of Object.entries(unusable)) {
      upstream({ compact });
      const svg = await expectCard(await get(COMPACT));
      const hrefs = calls.map((call) => call.href);
      assert.ok(hrefs.indexOf(`${RAW}panel-compact-dark.svg`) < hrefs.indexOf(`${RAW}panel-dark.svg`), label);
      assert.ok(svg.includes(`.artist{color:${PALETTE.dark.text}!important}`), label);
    }
    assert.ok(big.meter.served < 3 * MB, `pulled ${big.meter.served} bytes`);
  });

  it('accepts any height from 400 to 900 and no viewBox', async () => {
    for (const [options, height] of [[{ height: '400' }, 512], [{ height: '900' }, 1012], [{ viewBox: null }, 774]]) {
      upstream({ compact: () => ok(compactPanelSvg(options)) });
      const response = await get(COMPACT);
      assert.equal(response.status, 200);
      assert.match(await response.text(), new RegExp(`^<svg [^>]* width="360" height="${height}"`));
    }
  });

  it('answers 502 naming both panels when neither is usable', async () => {
    upstream({ compact: statusOnly(404), panel: statusOnly(404) });
    const missing = await expectFailure(await get(COMPACT), 502);
    assert.match(missing, /panel-compact-dark\.svg/);
    assert.match(missing, /panel-dark\.svg is unavailable/);
    upstream({ compact: statusOnly(404), panel: () => ok('<g/>') });
    const broken = await expectFailure(await get(COMPACT), 502);
    assert.match(broken, /panel-dark\.svg is not a usable SVG document/);
  });

  it('falls back within the deadline when the compact panel stalls', async () => {
    upstream({ compact: stall });
    const { result, ms } = await timed(() => get(COMPACT));
    await expectCard(result);
    assert.ok(ms > 2500 && ms < 5000, `${ms} ms`);
  });

  it('gives both panel fetches one deadline, so a compact card is never slower than a wide one', async () => {
    upstream({ compact: hang, panel: stall });
    const { result, ms } = await timed(() => get(COMPACT));
    await expectFailure(result, 502);
    assert.ok(ms > 5000 && ms < 5800, `${ms} ms, where one deadline per fetch would take 6000`);
  });

  it('falls back to the wide card when reading the compact panel throws', async () => {
    const trimEnd = String.prototype.trimEnd;
    String.prototype.trimEnd = function trimEndOrThrow() {
      if (this.includes('THROWS-WHEN-READ')) throw new RangeError('the reader failed');
      return trimEnd.call(this);
    };
    try {
      upstream({ compact: () => ok(compactPanelSvg({ extra: '<g id="THROWS-WHEN-READ"/>' })) });
      const svg = await expectCard(await get(COMPACT));
      assert.ok(svg.includes(`.artist{color:${PALETTE.dark.text}!important}`));
      assert.ok(calls.some((call) => call.href === `${RAW}panel-dark.svg`));
    } finally {
      String.prototype.trimEnd = trimEnd;
    }
  });
});

describe('Apple Music', () => {
  const appleCards = () => ok(appleCardsJson());
  const LABEL = 'aria-label="Coding activity and last played on Apple Music"';

  it('fetches the Apple Music card instead of Spotify, refusing redirects, under a deadline', async () => {
    upstream({ cards: appleCards });
    await get(`user=${USER}&mode=light`);
    assert.deepEqual(
      calls.map((call) => call.href).sort(),
      [`${RAW}cards.json`, `${RAW}panel-light.svg`, appleUrl(APPLE_UID, 'light')].sort(),
    );
    for (const { options } of calls) {
      assert.equal(options.redirect, 'error');
      assert.ok(options.signal instanceof AbortSignal);
    }
    upstream({ cards: appleCards });
    await get(COMPACT);
    assert.ok(calls.some((call) => call.href === appleUrl(APPLE_UID, 'dark')));
  });

  it('draws the wide card from the track alone, passing none of the service card on', async () => {
    upstream({ cards: appleCards });
    const svg = await expectCard(await get(`user=${USER}&mode=dark`));
    assert.ok(svg.includes(LABEL));
    assert.match(svg, /filter="url\(#relay-glow-playing\)">Last played on Apple Music<\/text>/);
    assert.match(svg, new RegExp(`fill="${PALETTE.dark.text}" filter="url\\(#relay-glow-artist\\)">Hélène &amp; Les Ondes</text>`));
    assert.match(svg, new RegExp(`fill="${PALETTE.dark.muted}">Bleu Nuit</text>`));
    assert.ok(svg.includes(`href="data:image/jpeg;base64,${RASTERS.jpeg}"`));
    assert.ok(svg.includes('fill="url(#vignetteRight)"'));
    assert.doesNotMatch(svg, /foreignObject|upstream|image\/webp|song-title|Nothing playing|Spotify/i);
  });

  it('draws the compact card strip from it', async () => {
    upstream({ cards: appleCards });
    const svg = await expectCompactCard(await get(COMPACT));
    assert.ok(svg.includes(LABEL));
    assert.match(svg, /lengthAdjust="spacing" filter="url\(#relay-glow-playing\)">Last played on Apple Music<\/text>/);
    assert.ok(svg.includes(`href="data:image/jpeg;base64,${RASTERS.jpeg}"`));
    assert.doesNotMatch(svg, /upstream|image\/webp|Nothing playing|Spotify/i);
  });

  it('escapes a hostile song and artist and keeps them as text', async () => {
    const song = '&lt;/text&gt;&lt;script&gt;alert(1)';
    const artist = '&lt;image href=&quot;x&quot;/&gt;';
    upstream({ cards: appleCards, apple: () => ok(appleSvg({ song, artist, extra: '<script>alert(2)</script>' })) });
    for (const query of [`user=${USER}&mode=light`, `user=${USER}&mode=light&layout=compact`]) {
      const response = await get(query);
      const svg = await response.text();
      assert.notEqual(svgInner(svg), null, query);
      assert.ok(svg.includes(`>${song}</text>`), query);
      assert.ok(svg.includes('>&lt;image href="x"/&gt;</text>'), query);
      assert.doesNotMatch(svg, /<script|alert\(2\)|<image href="x"/, query);
    }
  });

  it('draws a tile, never an outside image, for a cover that is not a base64 raster', async () => {
    for (const cover of ['https://evil.example/c.jpg', 'data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=', 'data:image/png;base64,AAAA']) {
      upstream({ cards: appleCards, apple: () => ok(appleSvg({ cover })) });
      const svg = await expectCard(await get(`user=${USER}&mode=light`));
      assert.ok(svg.includes(`<rect x="10" y="131" width="300" height="300" rx="5" fill="${PALETTE.light.line}"/>`), cover);
      assert.doesNotMatch(svg, /<image|data:image\/svg/, cover);
    }
  });

  it('shows the placeholder for the error card and anything else unusable', async () => {
    const unusable = {
      'an unknown uid': () => ok(appleErrorSvg()),
      'a lapsed session': () => ok(appleErrorSvg('Apple Music session expired, please link it again')),
      'a 422': () => new Response('{"type":"validation","on":"query","found":{}}', { status: 422 }),
      'a 500': statusOnly(500),
      'a JSON body': () => ok('{"type":"validation"}'),
      'a network error': networkError,
      'no song': () => ok(appleSvg({ song: '' })),
      'an unescaped ampersand': () => ok(appleSvg({ song: 'Rock & Roll' })),
    };
    for (const [label, apple] of Object.entries(unusable)) {
      upstream({ cards: appleCards, apple });
      const wide = await expectCard(await get(`user=${USER}&mode=light`));
      assert.match(wide, /Nothing playing/, label);
      assert.ok(wide.includes(LABEL), label);
      assert.doesNotMatch(wide, /Failure|expired|does not exist/, label);
      assert.match(await expectCompactCard(await get(`user=${USER}&mode=light&layout=compact`)), /Nothing playing/, label);
    }
  });

  it('does not ask Apple Music without a usable uid, nor when Spotify is named too', async () => {
    for (const uid of ['', 'a'.repeat(65), 'a/b', 'a&b=1', 42]) {
      upstream({ cards: () => ok(appleCardsJson({ uid })) });
      const svg = await expectCard(await get(`user=${USER}&mode=dark`));
      assert.match(svg, /Nothing playing/, String(uid));
      assert.ok(calls.every((call) => !call.href.startsWith(APPLE) && !call.href.startsWith(SPOTIFY)), String(uid));
    }
    upstream({ cards: () => ok(cardsJson({ apple_music: { uid: APPLE_UID } })) });
    const svg = await expectCard(await get(`user=${USER}&mode=dark`));
    assert.ok(svg.includes('<div class="artist">Mura Masa</div>'));
    assert.ok(calls.every((call) => !call.href.startsWith(APPLE)));
  });

  it('waits for a slow origin: a card that takes 5 s is still drawn', async () => {
    upstream({ cards: appleCards, apple: delayed(5000, () => ok(appleSvg())) });
    const { result, ms } = await timed(() => get(`user=${USER}&mode=dark`));
    assert.match(await expectCard(result), />Last played on Apple Music<\/text>/);
    assert.ok(ms > 5000 && ms < 6500, `${ms} ms`);
  });

  it('gives up on an origin that never answers after 8 s and shows the placeholder', async () => {
    upstream({ cards: appleCards, apple: hang });
    const { result, ms } = await timed(() => get(`user=${USER}&mode=dark`));
    assert.match(await expectCard(result), /Nothing playing/);
    assert.ok(ms > 7900 && ms < 8800, `${ms} ms`);
  });

  it('keeps the whole request within its 9 s budget after a slow cards.json', async () => {
    upstream({ cards: delayed(2500, appleCards), apple: hang });
    const { result, ms } = await timed(() => get(`user=${USER}&mode=dark`));
    assert.match(await expectCard(result), /Nothing playing/);
    assert.ok(ms > 8900 && ms < 9800, `${ms} ms, where the Apple Music deadline alone would take 10500`);
  });
});
