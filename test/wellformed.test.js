// Every card the relay serves must parse as XML: one error and Chrome draws nothing at all, the owner's panel
// included, where a refused music card would only have fallen back to the placeholder. This builds cards from
// the fixtures and from thousands of fragments made to trip a parser, and has Chrome's own XML parser read
// every card the relay would serve. It needs Chrome or Chromium, found where it usually installs or named by
// the CHROME environment variable, and is skipped without one.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

import { buildCard, buildCompactCard, compose, readCompactPanel, sanitize } from '../lib/compose.js';
import { COMPACT_PANEL_SVG, PALETTE, PANEL_SVG, RECENT_SVG, appleSvg, compactPanelSvg, spotifySvg } from './fixtures.js';

const XML_NS = 'http://www.w3.org/XML/1998/namespace';
const XMLNS_NS = 'http://www.w3.org/2000/xmlns/';
const XLINK = 'http://www.w3.org/1999/xlink';

function findChrome() {
  const local = process.env.LOCALAPPDATA ? join(process.env.LOCALAPPDATA, 'Google/Chrome/Application/chrome.exe') : null;
  return [
    process.env.CHROME,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    local,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ].find((path) => path && existsSync(path)) ?? null;
}

// Has Chrome parse each document as image/svg+xml, as it does a card, and returns, for each, null when it
// parsed or the parser's message.
function parseInChrome(chrome, docs) {
  const dir = mkdtempSync(join(tmpdir(), 'coderprint-wf-'));
  try {
    writeFileSync(join(dir, 'docs.js'), `window.DOCS = ${JSON.stringify(docs)};`, 'utf8');
    writeFileSync(join(dir, 'page.html'), `<!doctype html><meta charset="utf-8"><script src="docs.js"></script>
<pre id="out"></pre><script>
const verdicts = DOCS.map((text) => {
  const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
  const error = doc.getElementsByTagNameNS('http://www.w3.org/1999/xhtml', 'parsererror')[0];
  if (error) return error.textContent.replace(/\\s+/g, ' ').slice(0, 300);
  const root = doc.documentElement;
  return root.namespaceURI === 'http://www.w3.org/2000/svg' && root.localName === 'svg' ? null : 'not an svg root';
});
document.getElementById('out').textContent = encodeURIComponent(JSON.stringify(verdicts));
</script>`, 'utf8');
    const run = spawnSync(chrome, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
      `--user-data-dir=${join(dir, 'profile')}`, '--dump-dom', pathToFileURL(join(dir, 'page.html')).href],
    { encoding: 'utf8', timeout: 120_000, maxBuffer: 1 << 26 });
    const found = /<pre id="out">([^<]*)<\/pre>/.exec(run.stdout ?? '');
    assert.ok(found, `Chrome gave no verdicts: status ${run.status}, ${run.error ?? ''} ${(run.stderr ?? '').slice(0, 500)}`);
    return JSON.parse(decodeURIComponent(found[1]));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

// Fragments written by hand to trip a parser, most of them from the verifier's findings; each is also tried
// inside the real shapes of a panel and a widget.
const BY_HAND = [
  `<image xmlns:a="${XLINK}" a:href="#a" xlink:href="#b" width="1" height="1"/>`,
  `<g xmlns:x="${XML_NS}"/>`, '<g xmlns:xml="urn:x"/>', '<g xmlns:p=""/>', '<g xmlns:xmlns="urn:x"/>',
  `<g xmlns="${XMLNS_NS}"/>`, `<g xmlns:q="${XMLNS_NS}"/>`, `<g xmlns="${XML_NS}"/>`, '<xmlns:g/>', '<xml:g/>',
  '<g xmlns:a="urn:1" xmlns:b="urn:1" a:x="1" b:x="2"/>', `<g xmlns:a="${XLINK}" xlink:title="t" a:title="u"/>`,
  `<g xml:lang="en" xml:space="preserve"><text>ok</text></g>`, `<g xmlns:xml="${XML_NS}" xml:space="bogus" xml:id="1"/>`,
  `<g xmlns:xlink="${XLINK}X"><image xlink:href="#a" width="1" height="1"/></g>`, '<g xmlns:xlink="urn:y" xmlns:q="urn:y" xlink:a="1" q:a="2"/>',
  '<g xmlns:a="urn:x"><g xmlns:a="urn:y"><a:g a:z="1"/></g></g>', '<g xmlns:a="urn:1"><g xmlns:b="urn:1" a:x="1" b:x="2"/></g>',
  '<g href="#a" xlink:href="#b"/>', '<g xmlns=""><g/></g>', '<text>\u{1F600}\uD800</text>', '<text>]]<!-- -->></text>',
  '<style>a{b:c}</style><style>/* ok */</style>', '<text>ok &amp;amp; &#x20AC; &#65;</text>', '<text>a&#0;b</text>',
  '<text>a&#xFFFE;b</text>', '<text class="a&#x1B;b">x</text>', '<text>a&#xD800;b</text>', '<text>a&#x110000;b</text>',
  '<g xmlns:a="a b"/>', '<g xmlns:a="http://example.com/é"/>',
];

// BY_HAND and thousands more made from parts: namespace declarations, prefixed names and numeric references,
// and text joined across what the sanitizer drops.
function hostileFragments() {
  const fragments = new Set(BY_HAND);
  // Every pair of declarations over these prefixes and namespace names, each prefix then used for one
  // attribute of the same local name, on one element and across two.
  const prefixes = ['a', 'b', 'xml', 'xmlns', 'xlink'];
  const uris = ['urn:1', 'urn:&#49;', 'URN:1', XLINK, XML_NS, XMLNS_NS, '', ' urn:1', 'urn:1&#9;', 'a b', 'foo', '%zz', 'http://a:b:c/',
    'http://example.com/&#xE9;', 'http://example.com/\u00e9', 'a{b}', 'file:///x', 'mailto:a@b', 'http://[::1]/',
    'http://example.com:8080/p%20q/r?x=1&amp;y=/?#f/?', 'ht&#x74;p://a/b', 'http://a:65535/', 'http://a:99999/',
    'http://a:2147483647/', 'http://a:2147483648/', 'http://a:99999999999999999999/'];
  for (const u1 of uris) {
    fragments.add(`<g xmlns="${u1}"><g/></g>`);
    for (const p1 of prefixes) {
      fragments.add(`<${p1}:g xmlns:${p1}="${u1}"/>`);
      for (const p2 of prefixes) {
        for (const u2 of uris) {
          fragments.add(`<g xmlns:${p1}="${u1}" xmlns:${p2}="${u2}" ${p1}:x="1" ${p2}:x="2"/>`);
          fragments.add(`<g xmlns:${p1}="${u1}"><g xmlns:${p2}="${u2}" ${p1}:x="1" ${p2}:x="2"/></g>`);
        }
      }
    }
  }
  // Numeric references at the edges of what XML allows, in text and in attribute values.
  const codes = [0, 8, 9, 0xa, 0xb, 0xc, 0xd, 0x1f, 0x20, 0x7f, 0x85, 0xd7ff, 0xd800, 0xdbff, 0xdc00, 0xdfff, 0xe000, 0xfffd,
    0xfffe, 0xffff, 0x10000, 0x10ffff, 0x110000, 2 ** 32 + 65];
  for (const code of codes) {
    for (const ref of [`&#${code};`, `&#x${code.toString(16)};`, `&#x${code.toString(16).toUpperCase().padStart(8, '0')};`]) {
      fragments.add(`<text>a${ref}b</text>`);
      fragments.add(`<text class="a${ref}b">x</text>`);
      fragments.add(`<g xmlns:a="urn:${ref}"/>`);
    }
  }
  // Text on either side of whatever sanitize drops or rewrites.
  for (const before of ['', ']', ']]', 'a]']) {
    for (const between of ['', '<!-- -->', '<?x?>', '<script>x</script>', '<![CDATA[]]>', '<![CDATA[]]]>', '<![CDATA[]]]]>',
      '<![CDATA[>]]>', '<tspan/>']) {
      for (const after of ['>', ']>', 'x']) {
        fragments.add(`<text>${before}${between}${after}</text>`);
        fragments.add(`<style>${before}${between}${after}</style>`);
      }
    }
  }
  return [...fragments];
}

const chrome = findChrome();

test('every card the relay serves parses as XML in Chrome', { skip: chrome ? false : 'no Chrome found: set CHROME to a Chrome or Chromium binary', timeout: 240_000 }, () => {
  const cards = new Map(); // card text to what built it
  const add = (card, what) => {
    if (card !== null && !cards.has(card)) cards.set(card, what);
  };
  // The fixtures, as the relay serves them in both modes, wide and compact, with Spotify and Apple Music.
  const compact = readCompactPanel(COMPACT_PANEL_SVG);
  for (const mode of ['light', 'dark']) {
    const options = { glow: mode === 'dark' };
    for (const music of [spotifySvg(), RECENT_SVG, spotifySvg({ status: 'Recently played on' }), 'Not found']) {
      add(buildCard(PANEL_SVG, music, PALETTE[mode], options), `fixture wide ${mode}`);
      add(buildCompactCard(compact, music, PALETTE[mode], options), `fixture compact ${mode}`);
    }
    add(buildCard(PANEL_SVG, appleSvg(), PALETTE[mode], { ...options, service: 'apple' }), `fixture apple wide ${mode}`);
    add(buildCompactCard(compact, appleSvg(), PALETTE[mode], { ...options, service: 'apple' }), `fixture apple compact ${mode}`);
  }
  const nest = (n) => '<g>'.repeat(n) + '</g>'.repeat(n);
  add(buildCard(`<svg>${nest(250)}</svg>`, spotifySvg({ extra: nest(240) }), PALETTE.dark, { glow: true }), 'nested 250 deep');

  let kept = 0;
  let refused = 0;
  for (const fragment of hostileFragments()) {
    if (sanitize(fragment) === null) refused += 1;
    else kept += 1;
    // As a panel of its own, which is the smallest card that shows it.
    add(buildCard(`<svg>${fragment}</svg>`, 'Not found', PALETTE.light), fragment);
  }
  // The hand-written ones also inside the real shapes: the fixture panel, the Spotify widget, and the
  // compact panel.
  for (const fragment of BY_HAND) {
    add(buildCard(PANEL_SVG.replace(/<\/svg>\s*$/, `${fragment}</svg>`), spotifySvg({ extra: fragment }), PALETTE.dark, { glow: true }), fragment);
    add(buildCard(PANEL_SVG, RECENT_SVG.replace(/<\/svg>\s*$/, `${fragment}</svg>`), PALETTE.dark, { glow: true }), fragment);
    add(buildCompactCard(readCompactPanel(compactPanelSvg({ extra: fragment })), spotifySvg({ extra: fragment }), PALETTE.light), fragment);
  }
  // The corpus must hold both what the relay takes and what it refuses, or it proves nothing.
  assert.ok(kept > 500 && refused > 500, `kept ${kept}, refused ${refused}`);

  // The oracle must see a malformed card, or its silence proves nothing.
  const broken = compose('<g xmlns:a="urn:1" xmlns:b="urn:1" a:x="1" b:x="2"/>', '<text>&#0;</text>', PALETTE.light);
  const docs = [broken, ...cards.keys()];
  const verdicts = parseInChrome(chrome, docs);
  assert.equal(verdicts.length, docs.length);
  assert.ok(verdicts[0] !== null, 'Chrome parsed a malformed card');
  const failures = docs.slice(1).map((doc, i) => [cards.get(doc), verdicts[i + 1]]).filter(([, verdict]) => verdict !== null);
  assert.deepEqual(failures.slice(0, 20), [], `${failures.length} of ${docs.length - 1} served cards do not parse`);
});
