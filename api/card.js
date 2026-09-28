// GET /api/card?user=<login>&mode=dark|light[&layout=compact]
//
// Without layout the card is the wide one, 896 by 445. layout=compact asks for the portrait card for
// phones, 360 wide, built from the profile's panel-compact-<mode>.svg; a profile without a usable one
// gets the wide card instead, so it still shows something before it has drawn its compact panel. The
// music half is Spotify's widget or, when cards.json names an Apple Music uid instead, a card the relay
// draws itself from the track Apple Music's card names.
//
// A Vercel Function on the Node.js runtime, written as the fetch Web Standard export, per
// https://vercel.com/docs/functions/functions-api-reference#fetch-web-standard
// and https://vercel.com/docs/functions/runtimes/node-js (both read 26SEP2026). Files under /api
// deploy as functions; ES modules need "type": "module" in package.json, which this project sets.

import {
  appleUrl,
  buildCard,
  buildCompactCard,
  isAllowed,
  isLogin,
  isMode,
  rawUrl,
  readCards,
  readCompactPanel,
  spotifyUrl,
} from '../lib/compose.js';

const GITHUB_TIMEOUT_MS = 3000;
const SPOTIFY_TIMEOUT_MS = 2500;
// Apple Music's card comes from a single origin that caches nothing: it took 3.8 to 6.2 s on 26SEP2026.
const APPLE_TIMEOUT_MS = 8000;
// This repository sets no maximum duration for the function (no vercel.json, no exported config), so
// Vercel's default applies: 300 s on every plan with fluid compute, the default for new projects, but
// 10 s on the Hobby plan for a project deployed without it (https://vercel.com/docs/functions/limitations
// and Vercel's changelogs of 09MAY2024 and 25JUN2025, read 26SEP2026). So Apple Music's fetch also ends
// this long after the request began: however slowly cards.json answers, a request stays inside 10 s.
const REQUEST_BUDGET_MS = 9000;
// A compact request's panel fetches, the compact one and then, if it fails, the wide one, share one
// deadline as well as each having its own: no later than cards.json and then Spotify can take, so a
// compact card is never slower than a wide one.
const PANELS_TIMEOUT_MS = GITHUB_TIMEOUT_MS + SPOTIFY_TIMEOUT_MS;
const SVG_LIMIT_BYTES = 2 * 1024 * 1024;
const JSON_LIMIT_BYTES = 256 * 1024;

const CARD_HEADERS = {
  'Content-Type': 'image/svg+xml; charset=utf-8',
  'Cache-Control': 'public, max-age=0, s-maxage=10, stale-while-revalidate=86400, stale-if-error=86400',
  // Opened directly instead of through an <img>, an SVG is a live document; this keeps it inert, and
  // the sandbox stops it navigating anywhere, whatever slipped past the sanitizer.
  'Content-Security-Policy': "default-src 'none'; img-src data:; style-src 'unsafe-inline'; sandbox",
  'X-Content-Type-Options': 'nosniff',
};

export default {
  async fetch(request) {
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      return failure(405, 'Only GET and HEAD are supported.', { Allow: 'GET, HEAD' });
    }
    let response;
    try {
      response = await card(request);
    } catch {
      response = failure(500, 'The card could not be built.');
    }
    return request.method === 'HEAD'
      ? new Response(null, { status: response.status, headers: response.headers })
      : response;
  },
};

async function card(request) {
  const params = new URL(request.url).searchParams;
  const user = single(params, 'user');
  const mode = single(params, 'mode');
  // layout may be left out; when it is given, it has to be compact.
  const compact = params.has('layout');
  if (!isLogin(user) || !isMode(mode) || (compact && single(params, 'layout') !== 'compact')) {
    return failure(
      400,
      'Expected ?user=<GitHub login>&mode=dark or ?user=<GitHub login>&mode=light, optionally with &layout=compact.',
    );
  }
  if (!isAllowed(user, process.env.CODERPRINT_USERS)) {
    return failure(403, 'This relay does not serve that user. Deploy your own copy to use coderprint.');
  }

  const budget = AbortSignal.timeout(REQUEST_BUDGET_MS);
  // The panel and the data file load together; the music card waits only for the data file, which names
  // it, and then loads alongside the panel. The data file is coderprint.json, or for a profile drawn before
  // it existed cards.json: both are asked for at once, so the fallback costs no time.
  const panelLoad = loadPanel(user, mode, compact);
  const [dataText, legacyText] = await Promise.all([
    fetchText(rawUrl(user, 'coderprint.json'), JSON_LIMIT_BYTES, GITHUB_TIMEOUT_MS),
    fetchText(rawUrl(user, 'cards.json'), JSON_LIMIT_BYTES, GITHUB_TIMEOUT_MS),
  ]);
  const cards = (dataText === null ? null : readCards(dataText, mode))
    ?? (legacyText === null ? null : readCards(legacyText, mode));
  const service = cards?.apple ? 'apple' : 'spotify';
  let musicLoad = null;
  if (cards?.uid) {
    musicLoad = fetchText(spotifyUrl(cards.uid, cards.palette.bg), SVG_LIMIT_BYTES, SPOTIFY_TIMEOUT_MS);
  } else if (cards?.apple) {
    musicLoad = fetchText(appleUrl(cards.apple, mode), SVG_LIMIT_BYTES, APPLE_TIMEOUT_MS, budget);
  }
  const [panel, musicText] = await Promise.all([panelLoad, musicLoad]);

  if (cards === null) return failure(502, 'coderprint.json is unavailable or is not a JSON object.');
  const glow = mode === 'dark';
  if (panel.compact) {
    const svg = buildCompactCard(panel.compact, musicText, cards.palette, { glow, service });
    return new Response(svg, { status: 200, headers: CARD_HEADERS });
  }
  const wide = compact ? `panel-compact-${mode}.svg is not usable and panel-${mode}.svg` : `panel-${mode}.svg`;
  if (panel.wide === null) return failure(502, `${wide} is unavailable.`);
  const svg = buildCard(panel.wide, musicText, cards.palette, { glow, service });
  if (svg === null) return failure(502, `${wide} is not a usable SVG document.`);
  return new Response(svg, { status: 200, headers: CARD_HEADERS });
}

// Resolves to { compact } holding the checked compact panel when one was asked for and is usable, and
// otherwise to { wide } holding the wide panel's text, or null. The wide panel is fetched only once
// the compact one has failed, under the same size limit and its own deadline, and both within
// PANELS_TIMEOUT_MS, so a profile that has not drawn a compact panel yet still gets a card. Like
// fetchText, it never rejects: a panel the reader throws on counts as unusable.
async function loadPanel(user, mode, compact) {
  const panels = AbortSignal.timeout(PANELS_TIMEOUT_MS);
  if (compact) {
    const text = await fetchText(rawUrl(user, `panel-compact-${mode}.svg`), SVG_LIMIT_BYTES, GITHUB_TIMEOUT_MS, panels);
    let panel = null;
    try {
      panel = readCompactPanel(text);
    } catch {
      panel = null;
    }
    if (panel !== null) return { compact: panel };
  }
  return { wide: await fetchText(rawUrl(user, `panel-${mode}.svg`), SVG_LIMIT_BYTES, GITHUB_TIMEOUT_MS, panels) };
}

// A repeated parameter is as invalid as a missing one.
function single(params, name) {
  const values = params.getAll(name);
  return values.length === 1 ? values[0] : null;
}

function failure(status, message, extraHeaders = {}) {
  return new Response(`${message}\n`, {
    status,
    headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store', ...extraHeaders },
  });
}

// Resolves to the body as text, or to null on any failure: a status other than 2xx, a redirect,
// a timeout, the shared deadline passing when one is given, or a body over the limit. It never
// rejects, so an early return leaves nothing dangling.
async function fetchText(url, limitBytes, timeoutMs, shared = null) {
  const own = AbortSignal.timeout(timeoutMs);
  const signal = shared ? AbortSignal.any([own, shared]) : own;
  try {
    // Redirects are refused: the relay only ever talks to the hosts it names.
    const response = await fetch(url, { signal, redirect: 'error' });
    if (!response.ok || Number(response.headers.get('content-length')) > limitBytes) {
      await response.body?.cancel();
      return null;
    }
    return response.body ? await readCapped(response.body, limitBytes, signal) : '';
  } catch {
    return null;
  }
}

// Reads at most limitBytes and stops as soon as the body goes over, so a hostile upstream cannot
// exhaust memory. The timeout covers the body too: a stalled stream is cancelled on abort.
async function readCapped(body, limitBytes, signal) {
  // An abort that already happened would never fire the listener below.
  if (signal.aborted) return null;
  const reader = body.getReader();
  const stop = () => reader.cancel().catch(() => {});
  signal.addEventListener('abort', stop, { once: true });
  try {
    const chunks = [];
    let size = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (signal.aborted) return null;
      if (done) return new TextDecoder().decode(Buffer.concat(chunks));
      size += value.byteLength;
      if (size > limitBytes) {
        await stop();
        return null;
      }
      chunks.push(value);
    }
  } finally {
    signal.removeEventListener('abort', stop);
  }
}
