// GET /api/card?user=<login>&mode=dark|light
//
// A Vercel Function on the Node.js runtime, written as the fetch Web Standard export, per
// https://vercel.com/docs/functions/functions-api-reference#fetch-web-standard
// and https://vercel.com/docs/functions/runtimes/node-js (both read 26SEP2026). Files under /api
// deploy as functions; ES modules need "type": "module" in package.json, which this project sets.

import { buildCard, isAllowed, isLogin, isMode, rawUrl, readCards, spotifyUrl } from '../lib/compose.js';

const GITHUB_TIMEOUT_MS = 3000;
const SPOTIFY_TIMEOUT_MS = 2500;
const SVG_LIMIT_BYTES = 2 * 1024 * 1024;
const JSON_LIMIT_BYTES = 256 * 1024;

const CARD_HEADERS = {
  'Content-Type': 'image/svg+xml; charset=utf-8',
  'Cache-Control': 'public, max-age=0, s-maxage=10, stale-while-revalidate=86400, stale-if-error=86400',
  // Opened directly instead of through an <img>, an SVG is a live document; this keeps it inert.
  'Content-Security-Policy': "default-src 'none'; img-src data:; style-src 'unsafe-inline'",
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
  if (!isLogin(user) || !isMode(mode)) {
    return failure(400, 'Expected ?user=<GitHub login>&mode=dark or ?user=<GitHub login>&mode=light.');
  }
  if (!isAllowed(user, process.env.CODERPRINT_USERS)) {
    return failure(403, 'This relay does not serve that user. Deploy your own copy to use coderprint.');
  }

  // The panel and cards.json load together; Spotify waits only for cards.json, which names it.
  const panelLoad = fetchText(rawUrl(user, `panel-${mode}.svg`), SVG_LIMIT_BYTES, GITHUB_TIMEOUT_MS);
  const cardsText = await fetchText(rawUrl(user, 'cards.json'), JSON_LIMIT_BYTES, GITHUB_TIMEOUT_MS);
  const cards = cardsText === null ? null : readCards(cardsText, mode);
  const spotifyLoad = cards?.uid
    ? fetchText(spotifyUrl(cards.uid, cards.palette.bg), SVG_LIMIT_BYTES, SPOTIFY_TIMEOUT_MS)
    : null;
  const [panelText, spotifyText] = await Promise.all([panelLoad, spotifyLoad]);

  if (cards === null) return failure(502, 'cards.json is unavailable or is not a JSON object.');
  if (panelText === null) return failure(502, `panel-${mode}.svg is unavailable.`);
  const svg = buildCard(panelText, spotifyText, cards.palette);
  if (svg === null) return failure(502, `panel-${mode}.svg is not a usable SVG document.`);
  return new Response(svg, { status: 200, headers: CARD_HEADERS });
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
// a timeout, or a body over the limit. It never rejects, so an early return leaves nothing dangling.
async function fetchText(url, limitBytes, timeoutMs) {
  const signal = AbortSignal.timeout(timeoutMs);
  try {
    // Redirects are refused: the relay only ever talks to the two hosts it names.
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
