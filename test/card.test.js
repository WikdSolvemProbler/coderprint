import assert from 'node:assert/strict';
import { afterEach, beforeEach, describe, it } from 'node:test';

import handler from '../api/card.js';
import { BAR_RULES, DEFAULT_PALETTES, GLOW_RULES, spotifyUrl, svgInner } from '../lib/compose.js';
import { PALETTE, PANEL_SVG, cardsJson, spotifySvg } from './fixtures.js';

const USER = 'WikdSolvemProbler';
const UID = '1joahg6umn39flaqsl1c3j9n3';
const RAW = `https://raw.githubusercontent.com/${USER}/${USER}/HEAD/assets/`;
const SPOTIFY = 'https://spotify-github-profile.kittinanx.com/api/view?';
const CARD_CACHE = 'public, max-age=0, s-maxage=10, stale-while-revalidate=86400, stale-if-error=86400';
const MB = 1024 * 1024;

const realFetch = globalThis.fetch;
const realUsers = process.env.CODERPRINT_USERS;
let calls;

// Stands in for the three upstreams, routing each request by what it asks for.
function upstream({ cards = () => ok(cardsJson()), panel = () => ok(PANEL_SVG), spotify = () => ok(spotifySvg()) } = {}) {
  calls = [];
  globalThis.fetch = async (url, options) => {
    const href = String(url);
    calls.push({ href, options });
    if (href === `${RAW}cards.json`) return cards(options);
    if (href.startsWith(`${RAW}panel-`)) return panel(options);
    if (href.startsWith(SPOTIFY)) return spotify(options);
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
    const response = await get(`user=${USER}&mode=dark`);
    assert.match(response.headers.get('content-security-policy'), /default-src 'none'/);
    assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
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
