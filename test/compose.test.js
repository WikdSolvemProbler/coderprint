import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  COMPACT,
  DEFAULT_PALETTES,
  GLOW_RULES,
  appleUrl,
  buildCard,
  buildCompactCard,
  compose,
  isAllowed,
  isLogin,
  isMode,
  nowPlaying,
  placeholder,
  rawUrl,
  readCards,
  readCompactPanel,
  recentBars,
  recolor,
  sanitize,
  spotifyUrl,
  svgInner,
} from '../lib/compose.js';
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
  coderprintJson,
  compactPanelSvg,
  spotifySvg,
} from './fixtures.js';

const RULES_DARK =
  '.container{background:transparent!important}' +
  `.artist{color:${PALETTE.dark.text}!important}.song{color:${PALETTE.dark.muted}!important}` +
  '#bars{position:static!important;display:flex!important;align-items:flex-end;gap:1px;' +
  'width:auto!important;height:22px!important;margin:-22px 0 0!important;overflow:hidden}' +
  '.bar{position:static!important;flex:0 0 3px;opacity:1!important;animation-name:none!important}' +
  '@media (prefers-reduced-motion: no-preference){.bar{animation-name:cpbar!important}' +
  '@keyframes cpbar{from{height:3px}to{height:22px}}}';

// CSS with every block that opens with a match of start taken out, braces counted.
function withoutBlocks(css, start) {
  let rest = css;
  for (let found = start.exec(rest); found; found = start.exec(rest)) {
    let depth = 1;
    let end = found.index + found[0].length;
    for (; depth > 0 && end < rest.length; end += 1) depth += rest[end] === '{' ? 1 : rest[end] === '}' ? -1 : 0;
    rest = rest.slice(0, found.index) + rest.slice(end);
  }
  return rest;
}

// What a viewer who asks for reduced motion is left with: the style sheet without its
// @media (prefers-reduced-motion: no-preference) blocks.
function withoutMotion(css) {
  return withoutBlocks(css, /@media \(prefers-reduced-motion: no-preference\)\s*\{/);
}

// Every style element's text in a card, joined.
function styles(card) {
  return [...card.matchAll(/<style>([^<]*)<\/style>/g)].map(([, css]) => css).join('\n');
}

function withinMs(limit, run) {
  const start = performance.now();
  run();
  const elapsed = performance.now() - start;
  assert.ok(elapsed < limit, `took ${elapsed.toFixed(0)} ms`);
}

describe('isLogin', () => {
  it('accepts GitHub logins', () => {
    for (const login of ['a', 'Z9', 'WikdSolvemProbler', 'a-b', 'a-b-c', '1joah', 'x'.repeat(39)]) {
      assert.equal(isLogin(login), true, login);
    }
  });

  it('rejects everything else', () => {
    const bad = ['', '-a', 'a-', 'a--b', 'x'.repeat(40), 'a_b', 'a b', 'a.b', 'a/b', '../a', 'é', 'a\n', ' a'];
    for (const login of bad) assert.equal(isLogin(login), false, JSON.stringify(login));
    for (const value of [undefined, null, 42, ['a'], {}]) assert.equal(isLogin(value), false);
  });
});

describe('isMode', () => {
  it('accepts exactly dark and light', () => {
    assert.equal(isMode('dark'), true);
    assert.equal(isMode('light'), true);
    for (const value of ['Dark', 'LIGHT', 'dark ', '', 'auto', undefined, null]) assert.equal(isMode(value), false);
  });
});

describe('isAllowed', () => {
  it('matches case-insensitively and ignores spaces around names', () => {
    assert.equal(isAllowed('WikdSolvemProbler', 'someone, wikdsolvemprobler '), true);
    assert.equal(isAllowed('someone', 'Someone'), true);
  });

  it('allows nobody when the list is unset, empty or does not name the user', () => {
    assert.equal(isAllowed('someone', undefined), false);
    assert.equal(isAllowed('someone', ''), false);
    assert.equal(isAllowed('someone', ' , ,'), false);
    assert.equal(isAllowed('someone', 'someone2,another'), false);
    assert.equal(isAllowed('some', 'someone'), false);
  });
});

describe('URLs', () => {
  it('reads assets from the HEAD ref of the profile repository', () => {
    assert.equal(rawUrl('Octo-cat', 'cards.json'), 'https://raw.githubusercontent.com/Octo-cat/Octo-cat/HEAD/assets/cards.json');
  });

  it('asks the widget for the theme background without the hash', () => {
    assert.equal(
      spotifyUrl('abc123', '#100f0e'),
      'https://spotify-github-profile.kittinanx.com/api/view?uid=abc123&cover_image=true&theme=default' +
        '&show_offline=false&background_color=100f0e&interchange=false&profanity=false&hide_remaster=false',
    );
  });

  it('asks Apple Music for the theme and the uid, and nothing else', () => {
    assert.equal(appleUrl(APPLE_UID, 'dark'), `https://music-profile.rayriffy.com/theme/dark.svg?uid=${APPLE_UID}`);
    assert.equal(appleUrl('a.b', 'light'), 'https://music-profile.rayriffy.com/theme/light.svg?uid=a.b');
  });
});

describe('readCards', () => {
  it('takes a valid palette and uid', () => {
    assert.deepEqual(readCards(cardsJson(), 'dark'), { palette: PALETTE.dark, uid: '1joahg6umn39flaqsl1c3j9n3', apple: null });
    assert.deepEqual(readCards(cardsJson(), 'light').palette, PALETTE.light);
  });

  it('reads coderprint.json from its presentation, the same as cards.json from its top', () => {
    assert.deepEqual(readCards(coderprintJson(), 'dark'), readCards(cardsJson(), 'dark'));
    assert.deepEqual(readCards(coderprintJson(), 'light'), readCards(cardsJson(), 'light'));
    const hostile = { dark: { ...PALETTE.dark, bg: 'red;}' }, light: PALETTE.light };
    assert.deepEqual(readCards(coderprintJson({ palette: hostile }), 'dark').palette, DEFAULT_PALETTES.dark);
    assert.equal(readCards(coderprintJson({ uid: 'abc&evil=1' }), 'dark').uid, null);
    // a presentation that is not an object is ignored, so the top is read as before
    assert.deepEqual(readCards(JSON.stringify({ presentation: 'x', palette: PALETTE, spotify: { uid: 'abc' } }), 'dark'),
      { palette: PALETTE.dark, uid: 'abc', apple: null });
  });

  it('keeps only the four palette colors', () => {
    const palette = { dark: { ...PALETTE.dark, extra: '#000000' }, light: PALETTE.light };
    assert.deepEqual(Object.keys(readCards(cardsJson({ palette }), 'dark').palette), ['bg', 'text', 'muted', 'line']);
  });

  it('returns null for text that is not a JSON object', () => {
    for (const text of ['', 'not json', '<svg/>', '[]', '42', 'null', '"text"', '{"a":']) {
      assert.equal(readCards(text, 'dark'), null, text);
    }
  });

  it('falls back to the default palette for the whole mode when any color is invalid', () => {
    const hostile = ['red;}', 'red', '#fff', '#100f0e;}', '#100f0e\n', ' #100f0e', '#10 f0e', 16777215, null, ['#100f0e']];
    for (const text of hostile) {
      const palette = { dark: { ...PALETTE.dark, text }, light: PALETTE.light };
      assert.deepEqual(readCards(cardsJson({ palette }), 'dark').palette, DEFAULT_PALETTES.dark, JSON.stringify(text));
      assert.deepEqual(readCards(cardsJson({ palette }), 'light').palette, PALETTE.light);
    }
  });

  it('falls back when the palette is missing or the wrong shape', () => {
    for (const palette of [undefined, null, 'dark', [], { dark: [] }, { dark: 'x' }, { light: PALETTE.light }]) {
      assert.deepEqual(readCards(JSON.stringify({ palette }), 'dark').palette, DEFAULT_PALETTES.dark, JSON.stringify(palette));
    }
  });

  it('treats an invalid uid as absent', () => {
    for (const uid of ['', 'a'.repeat(65), 'abc&evil=1', 'abc def', '../x', 'é', 123, null, ['abc'], { uid: 'x' }]) {
      assert.equal(readCards(cardsJson({ uid }), 'dark').uid, null, JSON.stringify(uid));
    }
    assert.equal(readCards(cardsJson({ uid: 'a'.repeat(64) }), 'dark').uid, 'a'.repeat(64));
    assert.equal(readCards(JSON.stringify({ spotify: 'abc' }), 'dark').uid, null);
    assert.equal(readCards('{}', 'dark').uid, null);
  });

  it('takes an Apple Music uid, dots and all', () => {
    assert.deepEqual(readCards(appleCardsJson(), 'dark'), { palette: PALETTE.dark, uid: null, apple: APPLE_UID });
    assert.equal(readCards(appleCardsJson({ uid: 'a'.repeat(64) }), 'light').apple, 'a'.repeat(64));
    assert.equal(readCards('{}', 'dark').apple, null);
  });

  it('treats an invalid Apple Music uid as absent', () => {
    for (const uid of ['', 'a'.repeat(65), 'a/b', 'a b', 'a&b=1', '../x?y', 'a-b', 'é', 'a\n', 123, null, ['a'], { uid: 'a' }]) {
      assert.equal(readCards(appleCardsJson({ uid }), 'dark').apple, null, JSON.stringify(uid));
    }
    assert.equal(readCards(JSON.stringify({ apple_music: APPLE_UID }), 'dark').apple, null);
  });

  it('takes Spotify when a file names both', () => {
    const both = readCards(cardsJson({ apple_music: { uid: APPLE_UID } }), 'dark');
    assert.equal(both.uid, '1joahg6umn39flaqsl1c3j9n3');
    assert.equal(both.apple, null);
    assert.equal(readCards(cardsJson({ uid: 'no good', apple_music: { uid: APPLE_UID } }), 'dark').apple, APPLE_UID);
  });
});

describe('sanitize', () => {
  it('passes plain well formed markup through', () => {
    const markup = `<g id="a"><rect width="1" height="1"/><text x='1'>a &amp; b &lt; c &#169; &#xA9; "q" > r</text></g>`;
    assert.equal(sanitize(markup), markup);
    assert.equal(sanitize(''), '');
  });

  it('drops script elements with everything inside them', () => {
    const cases = [
      '<g><script>alert(1)</script></g>',
      '<g><SCRIPT type="text/javascript">alert(1)</SCRIPT></g>',
      '<g><script><![CDATA[ if (a < b) alert(1) ]]></script></g>',
      '<g><script href="#x"/></g>',
      '<g xmlns:s="http://www.w3.org/2000/svg"><s:script>alert(1)</s:script></g>',
      '<g><script><script>alert(1)</script></script></g>',
      '<g><iframe src="data:text/html,x"><p>alert(1)</p></iframe><object/><embed/></g>',
    ];
    for (const markup of cases) {
      const clean = sanitize(markup);
      assert.ok(clean !== null, markup);
      assert.doesNotMatch(clean, /script|alert|iframe|object|embed/i, markup);
    }
    assert.equal(sanitize('<g><script>alert(1)</script><rect/></g>'), '<g><rect/></g>');
  });

  it('drops event attributes', () => {
    const clean = sanitize(`<g onload="alert(1)" ONCLICK='x' onmouseover = "y" fill="red"><rect x:onfocus="z" xmlns:x="urn:x"/></g>`);
    assert.equal(clean, '<g fill="red"><rect xmlns:x="urn:x"/></g>');
  });

  it('keeps fragment and data links and drops every other link', () => {
    for (const url of ['#grid', ' #a', PIXEL, 'DATA:image/png;base64,AAAA']) {
      assert.equal(sanitize(`<use href="${url}"/>`), `<use href="${url}"/>`);
      assert.equal(sanitize(`<use xlink:href="${url}"/>`), `<use xlink:href="${url}"/>`);
    }
    const dropped = [
      'https://evil.example/x.svg#a',
      'http://evil.example',
      '//evil.example',
      'javascript:alert(1)',
      ' JavaScript:alert(1)',
      '&#106;avascript:alert(1)',
      '{}',
      'x.svg',
      '',
    ];
    for (const url of dropped) {
      assert.equal(sanitize(`<a href="${url}" target="_BLANK">x</a>`), '<a target="_BLANK">x</a>', url);
      assert.equal(sanitize(`<image xlink:href="${url}"/>`), '<image/>', url);
      assert.equal(sanitize(`<img src="${url}"/>`), '<img/>', url);
    }
    assert.equal(
      sanitize('<use l:href="https://evil.example" xmlns:l="http://www.w3.org/1999/xlink"/>'),
      '<use xmlns:l="http://www.w3.org/1999/xlink"/>',
    );
    assert.equal(sanitize(`<img srcset="${PIXEL} 1x, https://evil.example/a.png 2x"/>`), '<img/>');
  });

  it('stops animations from writing links or event handlers', () => {
    for (const target of ['href', 'xlink:href', 'onclick', ' onload ', '&#104;ref', 'x&#58;href']) {
      const clean = sanitize(`<a><set attributeName="${target}" to="javascript:alert(1)"/></a>`);
      assert.equal(clean, '<a><set to="javascript:alert(1)"/></a>', target);
    }
    const harmless = '<rect><animate attributeName="x" to="5"/></rect>';
    assert.equal(sanitize(harmless), harmless);
  });

  it('drops comments and processing instructions and turns CDATA into escaped text', () => {
    assert.equal(sanitize('<g><!-- note --><?xml-stylesheet href="https://evil.example/a.css"?></g>'), '<g></g>');
    assert.equal(
      sanitize('<style><![CDATA[a > b { fill: red } /* & */]]></style>'),
      '<style>a &gt; b { fill: red } /* &amp; */</style>',
    );
  });

  it('never loses track of where tags start inside CDATA, comments or quoted values', () => {
    const tricks = [
      `<g><![CDATA[<x y=']]><rect onload="alert(1)" z=' '/></g>`,
      `<g><!-- <x y=' --><rect onload="alert(1)" z=' '/></g>`,
      `<g title="a>b" onload="alert(1)"><rect title='"' onclick="alert(1)"/></g>`,
    ];
    for (const markup of tricks) {
      const clean = sanitize(markup);
      assert.ok(clean !== null, markup);
      assert.doesNotMatch(clean, /onload|onclick/, markup);
    }
  });

  it('returns null for anything that is not a well formed fragment', () => {
    const malformed = [
      'a < b',
      '<g>',
      '</g>',
      '<g></h>',
      '<g></g></g>',
      '</svg><svg>',
      '<g a=1/>',
      '<g a/>',
      '<g a="1"b="2"/>',
      '<g a="1" a="2"/>',
      '<g a="<"/>',
      '<g a="&x;"/>',
      '<p:g/>',
      '<g p:a="1"/>',
      '<g xmlns:p="urn:x"/><p:g/>',
      'AT&T',
      '&nbsp;',
      'a ]]> b',
      '<!-- open',
      '<![CDATA[ open',
      '<? open',
      '<!DOCTYPE x>',
      '< g/>',
      '<1/>',
      'a\x01b',
      '<scr<script>ipt>alert(1)</script>',
      '<div class="song"></style><script>alert(1)</script></div>',
    ];
    for (const markup of malformed) assert.equal(sanitize(markup), null, JSON.stringify(markup));
    assert.equal(sanitize(undefined), null);
  });

  it('accepts prefixes declared on the tag or an ancestor', () => {
    for (const markup of [
      '<p:g xmlns:p="urn:x" p:a="1"/>',
      '<g xmlns:p="urn:x"><p:g/></g>',
      '<use xlink:href="#a" xml:space="preserve"/>',
    ]) {
      assert.equal(sanitize(markup), markup);
    }
  });

  it('stays fast on pathological input', () => {
    const n = 200_000;
    const manyNames = Array.from({ length: n }, (_, i) => ` a${i}="c"`).join('');
    withinMs(2000, () => assert.equal(sanitize('<!--'.repeat(n)), null));
    withinMs(2000, () => assert.equal(sanitize('<![CDATA['.repeat(n)), null));
    withinMs(2000, () => assert.equal(sanitize('<a' + ' b="c"'.repeat(n)), null));
    withinMs(2000, () => assert.equal(sanitize('<a' + ' b="c"'.repeat(n) + '/>'), null));
    withinMs(2000, () => assert.notEqual(sanitize(`<a${manyNames}/>`), null));
    withinMs(2000, () => assert.equal(sanitize('<a b="' + 'x'.repeat(2_000_000)), null));
    withinMs(2000, () => assert.equal(sanitize('&#' + '1'.repeat(2_000_000)), null));
    withinMs(2000, () => assert.equal(sanitize('<g>'.repeat(n)), null));
    withinMs(2000, () => assert.notEqual(sanitize('<g>'.repeat(n) + '</g>'.repeat(n)), null));
    withinMs(2000, () => assert.equal(sanitize('a'.repeat(2_000_000) + '<'), null));
  });
});

describe('svgInner', () => {
  it('returns what lies between the root tags', () => {
    assert.equal(svgInner('<svg width="1"><g/></svg>'), '<g/>');
    const prolog = '\u{FEFF}<?xml version="1.0"?>\n<!-- c --><!DOCTYPE svg [<!ENTITY a "b">]>\n';
    assert.equal(svgInner(`${prolog}<svg>\n<g/>\n</svg >\n\n`), '\n<g/>\n');
    const inner = svgInner(PANEL_SVG);
    assert.match(inner, /^\n<style>/);
    assert.match(inner, /<pattern id="grid"/);
    assert.doesNotMatch(inner, /<\/svg>\s*$|^<svg/);
  });

  it('returns null when the root is not an svg element', () => {
    const notSvg = [
      '',
      'Not found',
      '{"svg": true}',
      '<html><body><svg><g/></svg></body></html>',
      '<!doctype html><svg></svg>',
      '<svgx></svgx>',
      '<svg/>',
      '<svg>',
      '<svg><g/>',
      '<svg><g/></svg><script>alert(1)</script>',
      '<svg></svg>trailing',
      '<svg><g></svg>',
      '<svg><g/></svg></svg>',
      'text<svg></svg>',
      '<svg a=1></svg>',
      '<svg:svg xmlns:svg="http://www.w3.org/2000/svg"></svg:svg>',
      '<?xml version="1.0"<svg></svg>',
    ];
    for (const text of notSvg) assert.equal(svgInner(text), null, JSON.stringify(text));
    for (const value of [undefined, null, 42, {}]) assert.equal(svgInner(value), null);
  });

  it('stays fast on pathological input', () => {
    withinMs(2000, () => assert.equal(svgInner('<?' + 'x'.repeat(2_000_000)), null));
    withinMs(2000, () => assert.equal(svgInner(' '.repeat(2_000_000) + 'x'), null));
    withinMs(2000, () => assert.equal(svgInner('<!--x-->'.repeat(200_000)), null));
    withinMs(2000, () => assert.equal(svgInner('<svg>' + '</svg> x'.repeat(200_000)), null));
  });
});

describe('recolor', () => {
  it('appends the overrides to the first style sheet', () => {
    const inner = svgInner(spotifySvg());
    const recolored = recolor(inner, PALETTE.dark);
    const at = recolored.indexOf('</style>');
    assert.equal(recolored.slice(at - RULES_DARK.length, at), RULES_DARK);
    assert.equal(recolored.replace(RULES_DARK, ''), inner);
  });

  it('is not fooled by an escaped closing tag in a song title', () => {
    const song = '&lt;/style&gt;&lt;script&gt;alert(1)&lt;/script&gt;';
    const recolored = recolor(svgInner(spotifySvg({ song })), PALETTE.dark);
    assert.ok(recolored.indexOf(RULES_DARK) < recolored.indexOf('class="song"'));
    assert.ok(recolored.includes(`<div class="song">${song}</div>`));
  });

  it('adds a style sheet when there is none', () => {
    assert.equal(recolor('<g/>', PALETTE.dark), `<style>${RULES_DARK}</style><g/>`);
  });
});

describe('placeholder', () => {
  it('is well formed, on theme and says nothing is playing', () => {
    const markup = placeholder(PALETTE.light);
    assert.equal(sanitize(markup), markup);
    assert.match(markup, />Nothing playing</);
    assert.match(markup, /text-anchor="middle"/);
    assert.ok(markup.includes(`fill="${PALETTE.light.muted}"`));
  });
});

describe('compose', () => {
  it('lays the panel and the right pane out exactly like the prototype', () => {
    const { bg, line } = PALETTE.dark;
    assert.equal(
      compose('PANEL', 'RIGHT', PALETTE.dark),
      '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="896" height="445" ' +
        'viewBox="0 0 896 445" role="img" aria-label="Coding activity and now playing on Spotify">' +
        `<rect width="896" height="445" rx="10" fill="${bg}"/>` +
        '<svg x="0" y="0" width="576" height="445" viewBox="0 0 576 445">PANEL</svg>' +
        `<rect x="560" width="336" height="445" rx="10" fill="${bg}"/>` +
        '<rect x="560" width="336" height="445" rx="10" fill="url(#grid)"/>' +
        `<line x1="576" y1="16" x2="576" y2="429" stroke="${line}"/>` +
        '<svg x="576" y="0" width="320" height="445" viewBox="0 0 320 445">RIGHT</svg>' +
        '</svg>',
    );
  });
});

describe('buildCard', () => {
  it('merges the panel and the recolored Spotify card into one well formed SVG', () => {
    const card = buildCard(PANEL_SVG, spotifySvg(), PALETTE.dark);
    assert.notEqual(svgInner(card), null);
    assert.ok(card.includes(RULES_DARK));
    assert.ok(card.includes('<div class="artist">Mura Masa</div>'));
    assert.ok(card.includes('<pattern id="grid"'));
    assert.ok(card.includes(`src="${PIXEL}"`));
    assert.doesNotMatch(card, /href="\{\}"|aria-labelledby|Nothing playing/);
  });

  it('strips scripts, handlers and outside links from both documents', () => {
    const extra = '<script>alert(1)</script><img src="https://evil.example/t.png" onerror="alert(2)"/>';
    const panel = PANEL_SVG.replace('<defs>', '<script><![CDATA[alert(3)]]></script><defs onload="alert(4)">');
    const card = buildCard(panel, spotifySvg({ extra }), PALETTE.dark);
    assert.notEqual(card, null);
    assert.doesNotMatch(card, /<script|alert|evil\.example|onerror|onload/i);
    assert.ok(card.includes(RULES_DARK));
  });

  it('keeps the right pane when the Spotify card is missing or unusable', () => {
    const unusable = [
      null,
      undefined,
      '',
      '<html><body>502 Bad Gateway</body></html>',
      '{"error":"not found"}',
      spotifySvg().slice(0, 1500),
      spotifySvg({ song: '</style><script>alert(1)</script>' }),
      spotifySvg({ song: 'Rock & Roll' }),
      spotifySvg({ song: '<script>alert(1)' }),
      spotifySvg({ extra: '<x:y/>' }),
    ];
    for (const spotify of unusable) {
      const card = buildCard(PANEL_SVG, spotify, PALETTE.light);
      assert.notEqual(svgInner(card), null);
      assert.match(card, /Nothing playing/);
      assert.doesNotMatch(card, /<script|alert/);
      assert.ok(card.includes(`fill="${PALETTE.light.muted}"`));
    }
  });

  it('returns null when the panel is not an SVG document', () => {
    for (const panel of [null, '', 'Not Found', '<html><svg></svg></html>', PANEL_SVG.replace('</svg>', ''), '<svg><g></svg>']) {
      assert.equal(buildCard(panel, spotifySvg(), PALETTE.dark), null, JSON.stringify(panel));
    }
  });
});

describe('recentBars', () => {
  const BAR = '<div class="bar"></div>';

  it('fills the empty equalizer of a recently played track with the bars the widget draws while playing', () => {
    const inner = svgInner(RECENT_SVG);
    assert.ok(inner.includes("<div id='bars'></div>"));
    assert.equal(new Set(inner.match(/\.bar:nth-child\(\d+\)/g)).size, 75);
    assert.equal(recentBars(inner), inner.replace("<div id='bars'></div>", `<div id='bars'>${BAR.repeat(75)}</div>`));
    const card = buildCard(PANEL_SVG, RECENT_SVG, PALETTE.dark, { glow: true });
    assert.notEqual(svgInner(card), null);
    assert.ok(card.includes(`<div id='bars'>${BAR.repeat(75)}</div>`));
    assert.ok(card.includes(`${RULES_DARK}${GLOW_RULES}</style>`), 'laid out by BAR_RULES, as a playing track is');
    assert.match(card, /<div class="playing">Recently played on <img class="logo"/);
  });

  it('leaves a playing track, a filled equalizer and a style that places no bars as they are', () => {
    for (const spotify of [spotifySvg(), spotifySvg({ status: 'Recently played on' }), spotifySvg({ artist: '' })]) {
      const inner = svgInner(spotify);
      assert.equal(recentBars(inner), inner);
    }
    const recent = svgInner(RECENT_SVG);
    for (const other of [recent.replace(/\.bar:nth-child\(\d+\)/g, '.x'), recent.replace('Recently played on', 'Now playing on')]) {
      assert.equal(recentBars(other), other);
    }
  });

  it('draws at most 100 bars, whatever the style places', () => {
    const rules = Array.from({ length: 5000 }, (_, i) => `.bar:nth-child(${i + 1}){left:1px}`).join('');
    const inner = svgInner(RECENT_SVG.replace('</style>', `${rules}</style>`));
    assert.equal(recentBars(inner).split(BAR).length - 1, 100);
  });

  it('holds the wide equalizer still under reduced motion, playing or recently played, and bounces it otherwise', () => {
    for (const spotify of [spotifySvg(), RECENT_SVG]) {
      for (const glow of [false, true]) {
        const card = buildCard(PANEL_SVG, spotify, PALETTE.dark, { glow });
        const css = styles(card);
        assert.ok(css.includes('@media (prefers-reduced-motion: no-preference){.bar{animation-name:cpbar!important}' +
          '@keyframes cpbar{from{height:3px}to{height:22px}}}'), 'bounces for a viewer who allows motion');
        const still = withoutMotion(css);
        assert.doesNotMatch(still, /cpbar/);
        assert.match(still, /(?:^|\})\.bar\{[^{}]*animation-name:none!important[^{}]*\}/, 'the widget\'s own animation is off');
        // Every other rule that still names an animation is the widget's own, for its bars, which the
        // important "none" above outranks: no bar, and nothing else, can move.
        const rules = withoutBlocks(still, /@keyframes\s+[\w-]+\s*\{/);
        for (const [, selector, body] of rules.matchAll(/([^{}]*)\{([^{}]*)\}/g)) {
          if (!/animation(?:-name)?\s*:/.test(body) || /animation-name:none!important/.test(body)) continue;
          for (const one of selector.split(',')) assert.match(one.trim(), /^\.bar(?::nth-child\(\s*\d+\s*\))?$/, `${selector}{${body}}`);
          assert.doesNotMatch(body, /!important/, body);
        }
      }
    }
  });
});

// Every id in a document, decoded, so that &#114;elay-x and relay-x count as the same one.
function ids(markup) {
  return [...markup.matchAll(/\s(?:[A-Za-z_][\w.-]*:)?id=("[^"]*"|'[^']*')/g)].map(([, quoted]) =>
    quoted.slice(1, -1).replace(/&#([0-9]+);/g, (_, code) => String.fromCodePoint(Number(code))),
  );
}

function compactCard(spotify = spotifySvg(), palette = PALETTE.dark, panel = COMPACT_PANEL_SVG) {
  return buildCompactCard(readCompactPanel(panel), spotify, palette, { glow: palette === PALETTE.dark });
}

describe('readCompactPanel', () => {
  it('reads the height and the sanitized markup of a portrait panel', () => {
    assert.deepEqual(readCompactPanel(COMPACT_PANEL_SVG), { inner: svgInner(COMPACT_PANEL_SVG), height: 662 });
    const fine = [
      [{ height: '400' }, 400],
      [{ height: '900' }, 900],
      [{ height: '662.5' }, 662.5],
      [{ viewBox: null }, 662],
      [{ viewBox: '0,0,360,662' }, 662],
      [{ viewBox: ' 0 0 360.0 662 ' }, 662],
    ];
    for (const [options, height] of fine) {
      assert.equal(readCompactPanel(compactPanelSvg(options))?.height, height, JSON.stringify(options));
    }
    assert.equal(COMPACT.width, 360);
  });

  it('returns null for anything but a panel 360 wide and 400 to 900 tall', () => {
    const widths = ['576', '360px', '', ' 360', '360.5', '+360', '3.6e2', 'auto', '100%'];
    const heights = ['399', '399.99', '900.01', '901', '662px', '-662', '', '1e3', '99999', ' 662'];
    const viewBoxes = ['0 0 576 445', '0 0 360', '0 0 360 662 1', '10 0 360 662', 'none', ''];
    const bad = [
      ...widths.map((width) => compactPanelSvg({ width, viewBox: null })),
      ...heights.map((height) => compactPanelSvg({ height, viewBox: null })),
      ...viewBoxes.map((viewBox) => compactPanelSvg({ viewBox })),
      COMPACT_PANEL_SVG.replace(' width="360"', ''),
      COMPACT_PANEL_SVG.replace(' height="662"', ''),
      PANEL_SVG,
      compactPanelSvg({ extra: '<x:y/>' }),
      COMPACT_PANEL_SVG.replace('</svg>', ''),
      '<svg width="360" height="662"><g></svg>',
      'Not Found',
      '',
      null,
    ];
    for (const text of bad) assert.equal(readCompactPanel(text), null, String(text).slice(0, 160));
  });

  it('sanitizes the panel as svgInner does', () => {
    const extra = '<script>alert(1)</script><g onload="alert(2)"><image href="https://evil.example/a.png"/></g>';
    const panel = readCompactPanel(compactPanelSvg({ extra }));
    assert.ok(panel.inner.includes('<g><image/></g>'));
    assert.doesNotMatch(panel.inner, /script|alert|evil/);
  });
});

describe('nowPlaying', () => {
  it('reads what the widget shows', () => {
    assert.deepEqual(nowPlaying(svgInner(spotifySvg())), {
      status: 'Now playing on',
      artist: 'Mura Masa',
      song: 'Love$ick (feat. A$AP Rocky)',
      cover: PIXEL,
      logo: PIXEL,
    });
    assert.equal(nowPlaying(svgInner(spotifySvg({ status: 'Recently played on' }))).status, 'Recently played on');
  });

  it('returns null when no artist is named', () => {
    const empty = [null, undefined, 42, '', '<g/>', '<div class="song">x</div>'];
    for (const artist of ['', ' \n\t ', '<span> </span>']) empty.push(svgInner(spotifySvg({ artist })));
    for (const inner of empty) assert.equal(nowPlaying(inner), null, JSON.stringify(inner));
  });

  it('decodes the text, collapses its white space and takes the first element of each class', () => {
    const inner =
      "<div class='artist other'>  A &amp;amp; B&#10; <span>C &#x1F3B5;</span>\t</div>" +
      '<div class="artist">second</div><div class="song">&lt;b&gt;</div><div class="song">third</div>';
    assert.deepEqual(nowPlaying(inner), { status: 'Now playing on', artist: 'A &amp; B C \u{1F3B5}', song: '<b>', cover: null, logo: null });
  });

  it('drops references to characters XML does not allow, without throwing', () => {
    const inner = '<div class="artist">a&#0;b&#xD800;c&#x110000;d&#99999999999999999999;e&#xFFFE;f&#x9;g</div>';
    assert.equal(nowPlaying(inner).artist, 'abcdef g');
  });

  it('takes the cover and logo only as data: rasters', () => {
    const refused = [
      'https://evil.example/c.png',
      'javascript:alert(1)',
      'data:text/html,x',
      'data:image/svg+xml;base64,AAAA',
      'data:image/pngx,AAAA',
      '#grid',
      '',
    ];
    for (const url of refused) {
      const inner = `<div class="artist">a</div><img class="cover" src="${url}"/><img class="logo" src="${url}"/>`;
      const playing = nowPlaying(inner);
      assert.equal(playing.cover, null, url);
      assert.equal(playing.logo, null, url);
    }
    for (const url of [' data:image/jpeg;base64, /9j/4AAQ', 'DATA:IMAGE/PNG;base64,AAAA', 'data:image/webp,AAAA', 'data:image/gif;base64,R0lG']) {
      assert.equal(nowPlaying(`<div class="artist">a</div><img class="cover" src="${url}"/>`).cover, url.trim(), url);
    }
    const lookalike = `<div class="artist">a</div><img class="cover" alt=' src="${PIXEL}"' src="https://evil.example/c.png"/>`;
    assert.equal(nowPlaying(lookalike).cover, null);
    assert.equal(nowPlaying(`<div class="artist">a</div><image class="cover" href="${PIXEL}"/>`).cover, null);
  });
});

describe('buildCompactCard', () => {
  it('returns null without a usable compact panel', () => {
    assert.equal(buildCompactCard(null, spotifySvg(), PALETTE.dark), null);
    assert.equal(buildCompactCard(readCompactPanel(PANEL_SVG), spotifySvg(), PALETTE.dark), null);
  });

  it('lays the panel over a native strip, like the prototype', () => {
    const { bg, text, muted, line } = PALETTE.light;
    const card = compactCard(spotifySvg(), PALETTE.light);
    assert.notEqual(svgInner(card), null);
    assert.ok(
      card.startsWith(
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="360" height="774" ' +
          'viewBox="0 0 360 774" role="img" aria-label="Coding activity and now playing on Spotify">' +
          '<defs><clipPath id="relay-card"><rect width="360" height="774" rx="10"/></clipPath></defs>' +
          `<rect width="360" height="774" rx="10" fill="${bg}"/>` +
          `<svg x="0" y="0" width="360" height="662" viewBox="0 0 360 662">${svgInner(COMPACT_PANEL_SVG)}</svg>` +
          '<rect y="662" width="360" height="112" fill="url(#grid)" clip-path="url(#relay-card)"/>' +
          `<line x1="14" y1="662" x2="346" y2="662" stroke="${line}"/>` +
          '<svg x="0" y="662" width="360" height="112" viewBox="0 0 360 112">',
      ),
    );
    assert.ok(card.endsWith('</svg></svg>'));
    assert.ok(card.includes(`<image x="14" y="14" width="84" height="84" preserveAspectRatio="xMidYMid slice" clip-path="url(#relay-cover)" href="${PIXEL}"/>`));
    assert.ok(card.includes('font-size="12" font-weight="700" fill="#53b14f" textLength="89.1" lengthAdjust="spacing">Now playing on</text>'));
    assert.ok(card.includes(`<image x="206.1" y="14" width="16" height="16" preserveAspectRatio="xMidYMid meet" href="${PIXEL}"/>`));
    assert.match(card, new RegExp(`<text x="112" y="53" [^>]*font-size="17" font-weight="700" fill="${text}">Mura Masa</text>`));
    assert.match(card, new RegExp(`<text x="112" y="73" [^>]*font-size="14" fill="${muted}">Love\\$ick \\(feat\\. A\\$AP Rocky\\)</text>`));
    const bars = card.match(
      /<rect class="relay-bar" x="\d+" y="\d+" width="3" height="\d+" rx="1" fill="#53b14f" fill-opacity=".55" style="animation-duration:\d+ms"\/>/g,
    );
    assert.equal(bars.length, 47);
    assert.equal(compactCard(spotifySvg(), PALETTE.light), card, 'the same song draws the same equalizer');
    assert.doesNotMatch(card, /<div|foreignObject|<style>\s*div|filter|vignette|Nothing playing/);
  });

  it('escapes what the widget says, quotes in a cover URL included', () => {
    const cover = 'data:image/png;base64,AA&quot;/&gt;&lt;x';
    const card = compactCard(spotifySvg({ artist: 'A &amp; B &lt;i&gt;', song: '&apos;&quot;&#60;', cover }), PALETTE.light);
    assert.notEqual(svgInner(card), null);
    assert.ok(card.includes('>A &amp; B &lt;i&gt;</text>'));
    assert.ok(card.includes(`>'"&lt;</text>`));
    assert.ok(card.includes(`href="data:image/png;base64,AA&quot;/&gt;&lt;x"`));
    assert.doesNotMatch(card, /<i>|<x/);
  });

  it('cuts long lines with an ellipsis, counting wide characters as wide and never splitting one', () => {
    const artistOf = (artist) => compactCard(spotifySvg({ artist }), PALETTE.light).match(/font-size="17"[^>]*>([^<]*)<\/text>/)[1];
    const songOf = (song) => compactCard(spotifySvg({ song }), PALETTE.light).match(/font-size="14"[^>]*>([^<]*)<\/text>/)[1];
    assert.equal(artistOf('x'.repeat(22)), 'x'.repeat(22));
    assert.equal(artistOf('x'.repeat(23)), `${'x'.repeat(21)}…`);
    assert.equal(artistOf('Mura   Masa and a long list of friends'), 'Mura Masa and a long…');
    assert.equal(artistOf('日本語'.repeat(10)), `${'日本語'.repeat(10).slice(0, 13)}…`);
    const family = '\u{1F469}‍\u{1F469}‍\u{1F467}';
    assert.equal(artistOf(family.repeat(20)), `${family.repeat(13)}…`);
    assert.equal(songOf('y'.repeat(32)), 'y'.repeat(32));
    assert.equal(songOf('y'.repeat(33)), `${'y'.repeat(31)}…`);
    withinMs(2000, () => assert.equal(artistOf('z'.repeat(1_000_000)), `${'z'.repeat(21)}…`));
  });

  it('draws a tile in place of a cover that is not a data: raster, and no logo', () => {
    for (const url of ['#grid', 'https://evil.example/c.png']) {
      const card = compactCard(spotifySvg({ cover: url, logo: url }), PALETTE.light);
      assert.ok(card.includes(`<rect x="14" y="14" width="84" height="84" rx="5" fill="${PALETTE.light.line}"/>`), url);
      assert.ok(!card.includes('clip-path="url(#relay-cover)"') && !card.includes(`href="${url}"`), url);
      assert.doesNotMatch(card, /<image/, url);
      assert.ok(card.includes('>Mura Masa</text>'), url);
    }
  });

  it('sets the widget status to its width and puts the logo after it', () => {
    const card = compactCard(spotifySvg({ status: 'Recently played on' }), PALETTE.light);
    assert.ok(card.includes('textLength="108.3" lengthAdjust="spacing">Recently played on</text>'));
    assert.ok(card.includes('<image x="225.3" y="14" width="16" height="16"'));
  });

  it('sets the status from real glyph widths, within 2% of Segoe UI Bold and Arial Bold at 12', () => {
    // Widths of the widget's two status lines measured in Chrome (canvas measureText, bold 12px).
    const measured = { 'Now playing on': [89.47, 88.66], 'Recently played on': [106.86, 109.37] };
    for (const [status, widths] of Object.entries(measured)) {
      const set = Number(compactCard(spotifySvg({ status }), PALETTE.light).match(/textLength="([\d.]+)"/)[1]);
      for (const width of widths) assert.ok(Math.abs(set - width) / width < 0.02, `${status}: ${set} against ${width}`);
    }
  });

  it('counts symbols drawn as emoji, flags and capitals wider, and clips the text column at the padding', () => {
    const artistOf = (artist) => compactCard(spotifySvg({ artist }), PALETTE.light).match(/font-size="17"[^>]*>([^<]*)<\/text>/)[1];
    const songOf = (song) => compactCard(spotifySvg({ song }), PALETTE.light).match(/font-size="14"[^>]*>([^<]*)<\/text>/)[1];
    for (const wide of ['☀', '❤', '✨', '⭐', '\u{1F1EF}\u{1F1F5}', '\u{1F004}']) {
      assert.equal(artistOf(wide.repeat(13)), wide.repeat(13), wide);
      assert.equal(artistOf(wide.repeat(14)), `${wide.repeat(13)}…`, wide);
    }
    assert.equal(artistOf('M'.repeat(19)), 'M'.repeat(19));
    assert.equal(artistOf('M'.repeat(20)), `${'M'.repeat(18)}…`);
    assert.equal(songOf('M'.repeat(24)), 'M'.repeat(24));
    assert.equal(songOf('M'.repeat(25)), `${'M'.repeat(23)}…`);
    const card = compactCard(spotifySvg(), PALETTE.dark);
    assert.ok(card.includes('<clipPath id="relay-text"><rect width="346" height="112"/></clipPath>'));
    const column = card.match(/<g clip-path="url\(#relay-text\)">(.*?)<\/g>/)[1];
    assert.equal(column.match(/<text /g).length, 3);
    assert.ok(column.includes('>Now playing on</text><image ') && column.includes('>Mura Masa</text>'));
  });

  it('bounces the equalizer, playing or recently played, only for a viewer who allows motion', () => {
    const motion =
      '<style>@media (prefers-reduced-motion: no-preference){@keyframes relay-bounce{to{transform:scaleY(.2)}}' +
      '.relay-bar{transform-box:fill-box;transform-origin:50% 100%;animation:relay-bounce 425ms linear infinite alternate}}</style>';
    for (const spotify of [spotifySvg(), RECENT_SVG]) {
      for (const palette of [PALETTE.light, PALETTE.dark]) {
        const card = compactCard(spotify, palette);
        assert.equal(card.split(motion).length, 2);
        const bars = [...card.matchAll(/<rect class="relay-bar" x="\d+" y="(\d+)" width="3" height="(\d+)"[^>]* style="animation-duration:(\d+)ms"\/>/g)];
        assert.equal(bars.length, 47);
        for (const [, y, height, pace] of bars) {
          assert.equal(Number(y) + Number(height), 98, 'at rest every bar stands on the baseline at its full height');
          assert.ok(Number(pace) >= 350 && Number(pace) <= 500, pace);
        }
        assert.ok(new Set(bars.map((bar) => bar[3])).size > 10, 'each bar keeps a pace of its own');
      }
    }
    assert.match(compactCard(RECENT_SVG, PALETTE.light), /lengthAdjust="spacing">Recently played on<\/text>/);
    assert.doesNotMatch(compactCard(spotifySvg({ artist: '' })), /bounce|relay-bar/);
  });

  it('says nothing is playing, without glow, when the widget has nothing to show', () => {
    for (const spotify of [null, '', '{"error":"not found"}', spotifySvg({ artist: '' }), spotifySvg({ song: 'Rock & Roll' })]) {
      const card = compactCard(spotify);
      assert.notEqual(svgInner(card), null);
      assert.ok(card.includes(`<g transform="translate(20 -165)">${placeholder(PALETTE.dark)}</g>`));
      assert.doesNotMatch(card, /relay-glow|<text[^>]*>(?!Nothing playing|NORMALIZED)/);
      assert.ok(card.includes('fill="url(#relay-vignette)"'), 'the vignette is dark mode, playing or not');
    }
  });

  it('glows in dark mode only, with the shadows GLOW_RULES gives the wide card', () => {
    const dark = compactCard();
    const light = compactCard(spotifySvg(), PALETTE.light);
    const shadows = {
      playing: /\.playing\{text-shadow:0 0 ([\d.]+)px rgba\((\d+),(\d+),(\d+),([\d.]+)\)\}/,
      artist: /\.artist\{text-shadow:0 0 ([\d.]+)px rgba\((\d+),(\d+),(\d+),([\d.]+)\)\}/,
      bars: /\.bar\{box-shadow:0 0 ([\d.]+)px rgba\((\d+),(\d+),(\d+),([\d.]+)\)\}/,
    };
    for (const [name, rule] of Object.entries(shadows)) {
      const [, blur, ...rgba] = GLOW_RULES.match(rule);
      const color = `#${rgba.slice(0, 3).map((n) => Number(n).toString(16).padStart(2, '0')).join('')}`;
      assert.ok(
        dark.includes(
          `<filter id="relay-glow-${name}" filterUnits="userSpaceOnUse" x="0" y="0" width="360" height="112" ` +
            'color-interpolation-filters="sRGB">' +
            `<feGaussianBlur in="SourceAlpha" stdDeviation="${Number(blur) / 2}" result="blur"/>` +
            `<feFlood flood-color="${color}" flood-opacity="${Number(rgba[3])}"/>`,
        ),
        name,
      );
      assert.equal(dark.split(`filter="url(#relay-glow-${name})"`).length, 2, name);
    }
    assert.match(dark, /<g filter="url\(#relay-glow-bars\)"><rect/);
    assert.match(dark, /<text [^>]*font-size="14" fill="[^"]*">Love/, 'the song does not glow, as in the wide card');
    assert.ok(
      dark.includes(
        '<radialGradient id="relay-vignette" cx="50%" cy="48%" r="75%"><stop offset=".62" stop-color="#000" ' +
          'stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".22"/></radialGradient>',
      ),
    );
    assert.ok(dark.endsWith('<rect y="662" width="360" height="112" fill="url(#relay-vignette)" clip-path="url(#relay-card)"/></svg>'));
    assert.doesNotMatch(light, /<filter|filter=|vignette/);
  });

  it('keeps its own ids clear of every id in the panel', () => {
    assert.ok(compactCard().includes('<clipPath id="relay-card">'));
    const extra = `<g id="relay-card"/><g id="&#114;elay1-cover"/><g id='relay3-x'/><g xml:id="relay2x"/>`;
    const card = compactCard(spotifySvg(), PALETTE.dark, compactPanelSvg({ extra }));
    for (const name of ['card', 'cover', 'glow-playing', 'glow-artist', 'glow-bars', 'vignette']) {
      assert.ok(card.includes(`id="relay2-${name}"`), name);
      assert.ok(card.includes(`url(#relay2-${name})`), name);
    }
    const all = ids(card);
    assert.equal(new Set(all).size, all.length, all.join(' '));
  });

  it('runs the panel and the widget through the sanitizer', () => {
    const extra = '<script>alert(1)</script><rect onclick="alert(2)"/>';
    const card = compactCard(spotifySvg({ extra: '<script>alert(3)</script>' }), PALETTE.dark, compactPanelSvg({ extra }));
    assert.notEqual(svgInner(card), null);
    assert.doesNotMatch(card, /script|alert|onclick/);
  });
});

describe('nowPlaying for Apple Music', () => {
  const read = (card) => nowPlaying(svgInner(card), 'apple');

  it('reads the song, the artist and the cover, relabelled by its bytes', () => {
    assert.deepEqual(read(appleSvg()), {
      status: 'Last played on Apple Music',
      artist: 'Hélène & Les Ondes',
      song: 'Bleu Nuit',
      cover: `data:image/jpeg;base64,${RASTERS.jpeg}`,
      logo: null,
    });
  });

  it('labels a cover by its bytes, whatever the service called it', () => {
    const cases = [
      [`data:image/webp;base64,${RASTERS.jpeg}`, 'image/jpeg', RASTERS.jpeg],
      [`data:image/png;base64,${RASTERS.gif}`, 'image/gif', RASTERS.gif],
      [`data:image/jpeg;base64,${RASTERS.webp}`, 'image/webp', RASTERS.webp],
      [`data:image/webp;base64,${RASTERS.png}`, 'image/png', RASTERS.png],
      [`DATA:IMAGE/WEBP;BASE64, ${RASTERS.jpeg.slice(0, 40)}\n ${RASTERS.jpeg.slice(40)}`, 'image/jpeg', RASTERS.jpeg],
    ];
    for (const [cover, type, data] of cases) assert.equal(read(appleSvg({ cover })).cover, `data:${type};base64,${data}`, cover.slice(0, 30));
  });

  it('takes no cover but a base64 PNG, JPEG, GIF or WebP image', () => {
    const refused = [
      'https://evil.example/c.jpg',
      '#grid',
      'javascript:alert(1)',
      'data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=',
      'data:text/html;base64,PGI+eDwvYj4=',
      `data:image/webp,${RASTERS.jpeg}`,
      'data:image/png;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciLz4=',
      'data:image/png;base64,AAAA',
      'data:image/webp;base64,UklGRgAAAABBVkkg',
      'data:image/jpeg;base64,/9j/4AA*',
      'data:image/jpeg;base64,/9j/4A',
      'data:image/webp;base64,',
      '',
    ];
    for (const cover of refused) {
      const playing = read(appleSvg({ cover }));
      assert.equal(playing.cover, null, cover);
      assert.equal(playing.song, 'Bleu Nuit', cover);
    }
    assert.equal(read(appleSvg().replace(/<img [^>]*\/>/, '<div class="cover-image"/>')).cover, null);
  });

  it('is null for the error card, and for a card without both a song and an artist', () => {
    const unusable = [
      appleErrorSvg(),
      appleErrorSvg('Apple Music session expired'),
      appleSvg({ song: '' }),
      appleSvg({ artist: ' \n ' }),
      appleSvg({ song: '</h1><script>alert(1)</script><h1>' }),
      appleSvg().replace('<h1 class="song-title upstream-style">', '<h1 class="title">'),
      appleSvg().replace('<h2 class="upstream-style song-artist">', '<h3 class="song-artist">').replace('</h2>', '</h3>'),
      appleSvg({ extra: '<h1>Failure!</h1>' }),
      appleSvg({ extra: '<svg xmlns="http://www.w3.org/2000/svg" class="bug-icon"><path d="M0 0"/></svg>' }),
      spotifySvg(),
      null,
      '',
      '<g/>',
    ];
    for (const card of unusable) assert.equal(read(card), null, String(card).slice(0, 240));
  });

  it('decodes the text and takes only the first h1.song-title and h2.song-artist', () => {
    const inner =
      '<div class="song-title">not a heading</div><h2 class="song-title">nor this</h2>' +
      '<h1 class="song-title x">&lt;/text&gt;&lt;script&gt; &amp;amp;\n &#x1F3B5;</h1><h2 class="song-artist">A&#0;B</h2>' +
      '<h1 class="song-title">second</h1><h2 class="song-artist">second</h2>';
    assert.deepEqual(nowPlaying(inner, 'apple'), {
      status: 'Last played on Apple Music',
      artist: 'AB',
      song: '</text><script> &amp; \u{1F3B5}',
      cover: null,
      logo: null,
    });
  });
});

describe('the Apple Music card', () => {
  const card = (music = appleSvg(), palette = PALETTE.dark, panel = PANEL_SVG) =>
    buildCard(panel, music, palette, { glow: palette === PALETTE.dark, service: 'apple' });
  const LABEL = 'aria-label="Coding activity and last played on Apple Music"';
  const PANE = '<svg x="576" y="0" width="320" height="445" viewBox="0 0 320 445">';

  it('draws its own pane from the song, the artist and the cover, and passes none of the service card on', () => {
    const { text, muted } = PALETTE.light;
    const svg = card(appleSvg(), PALETTE.light);
    assert.notEqual(svgInner(svg), null);
    assert.ok(svg.includes(LABEL) && svg.includes(PANE));
    assert.ok(svg.includes(`<svg x="0" y="0" width="576" height="445" viewBox="0 0 576 445">${svgInner(PANEL_SVG)}</svg>`));
    assert.match(svg, /<text x="160" y="32" text-anchor="middle" [^>]*font-size="16" font-weight="700" fill="#53b14f">Last played on Apple Music<\/text>/);
    assert.match(svg, new RegExp(`<text x="160" y="76" text-anchor="middle" [^>]*font-size="20" font-weight="700" fill="${text}">Hélène &amp; Les Ondes</text>`));
    assert.match(svg, new RegExp(`<text x="160" y="101" text-anchor="middle" [^>]*font-size="16" fill="${muted}">Bleu Nuit</text>`));
    assert.ok(
      svg.includes(
        '<image x="10" y="131" width="300" height="300" preserveAspectRatio="xMidYMid slice" clip-path="url(#relay-cover)" ' +
          `href="data:image/jpeg;base64,${RASTERS.jpeg}"/>`,
      ),
    );
    assert.doesNotMatch(svg, /foreignObject|<div|<h1|<h2|<p[ >]|upstream|song-title|song-artist|cover-image|image\/webp|Spotify|Nothing playing/i);
  });

  it('bounces a full-width equalizer on the cover, only for a viewer who allows motion', () => {
    const svg = card();
    const bars = [
      ...svg.matchAll(
        /<rect class="relay-bar" x="(\d+)" y="(\d+)" width="3" height="(\d+)" rx="1" fill="#53b14f" fill-opacity=".55" style="animation-duration:(\d+)ms"\/>/g,
      ),
    ];
    assert.equal(bars.length, 60);
    assert.deepEqual([bars[0][1], bars.at(-1)[1]], ['10', '305']);
    for (const [, , y, height, pace] of bars) {
      assert.equal(Number(y) + Number(height), 129, 'at rest every bar stands on the cover at its full height');
      assert.ok(Number(height) >= 3 && Number(height) <= 21, height);
      assert.ok(Number(pace) >= 350 && Number(pace) <= 500, pace);
    }
    assert.ok(new Set(bars.map((bar) => bar[3])).size > 15, 'the bars differ in height');
    assert.ok(new Set(bars.map((bar) => bar[4])).size > 20, 'each bar keeps a pace of its own');
    assert.equal(svg.split('<style>@media (prefers-reduced-motion: no-preference){@keyframes relay-bounce{').length, 2);
    assert.equal(card(), svg, 'the same track draws the same equalizer');
  });

  it('glows in dark mode only, as the Spotify half does, under the same vignette', () => {
    const dark = card();
    for (const name of ['playing', 'artist', 'bars']) {
      assert.ok(dark.includes(`<filter id="relay-glow-${name}" filterUnits="userSpaceOnUse" x="0" y="0" width="320" height="445" `), name);
      assert.equal(dark.split(`filter="url(#relay-glow-${name})"`).length, 2, name);
    }
    assert.match(dark, /<text [^>]*font-size="16" fill="[^"]*">Bleu Nuit<\/text>/, 'the song does not glow');
    assert.ok(dark.endsWith(`<rect x="560" width="336" height="445" rx="10" fill="url(#vignetteRight)"/></svg>`));
    assert.doesNotMatch(card(appleSvg(), PALETTE.light), /<filter|filter=|vignette/);
  });

  it('keeps its ids clear of the panel', () => {
    const panel = PANEL_SVG.replace('<circle', '<g id="relay-cover"/><g id="&#114;elay1-glow-bars"/><circle');
    const svg = card(appleSvg(), PALETTE.dark, panel);
    for (const name of ['cover', 'glow-playing', 'glow-artist', 'glow-bars']) {
      assert.ok(svg.includes(`id="relay2-${name}"`) && svg.includes(`url(#relay2-${name})`), name);
    }
    assert.ok(svg.includes('class="relay2-bar"') && svg.includes('@keyframes relay2-bounce'));
    const all = ids(svg);
    assert.equal(new Set(all).size, all.length, all.join(' '));
  });

  it('shows the placeholder, under its own label, when the card is unusable', () => {
    const unusable = [null, '', '{"type":"validation","on":"query","found":{}}', appleErrorSvg(), appleSvg({ song: 'Rock & Roll' }),
      appleSvg({ artist: '' }), spotifySvg()];
    for (const music of unusable) {
      const svg = card(music, PALETTE.light);
      assert.notEqual(svgInner(svg), null);
      assert.ok(svg.includes(`${PANE}${placeholder(PALETTE.light)}</svg>`), String(music).slice(0, 80));
      assert.ok(svg.includes(LABEL));
      assert.doesNotMatch(svg, /Failure|does not exist|relay-bar|<image|Mura/);
    }
  });

  it('escapes a hostile song and artist and keeps them as text', () => {
    const song = '&lt;/text&gt;&lt;script&gt; ]]&gt; &quot;&apos;';
    const artist = '&lt;image href=&quot;x&quot;/&gt;';
    const svg = card(appleSvg({ song, artist }), PALETTE.light);
    assert.notEqual(svgInner(svg), null);
    assert.ok(svg.includes(`>&lt;/text&gt;&lt;script&gt; ]]&gt; "'</text>`));
    assert.ok(svg.includes('>&lt;image href="x"/&gt;</text>'));
    assert.doesNotMatch(svg, /<script|<image href="x"|\]\]>/);
  });

  it('cuts a long song or artist to the pane with an ellipsis', () => {
    const svg = card(appleSvg({ song: 'y'.repeat(200), artist: 'z'.repeat(200) }), PALETTE.light);
    assert.equal(svg.match(/font-size="20" font-weight="700" fill="[^"]*">([^<]*)<\/text>/)[1], `${'z'.repeat(24)}…`);
    assert.equal(svg.match(/font-size="16" fill="[^"]*">([^<]*)<\/text>/)[1], `${'y'.repeat(35)}…`);
    withinMs(2000, () => card(appleSvg({ song: 'w'.repeat(1_000_000) })));
  });

  it('draws a tile in place of a cover that is not a base64 raster', () => {
    for (const cover of ['https://evil.example/c.jpg', 'data:image/png;base64,AAAA', `data:image/webp,${RASTERS.jpeg}`]) {
      const svg = card(appleSvg({ cover }), PALETTE.light);
      assert.ok(svg.includes(`<rect x="10" y="131" width="300" height="300" rx="5" fill="${PALETTE.light.line}"/>`), cover);
      assert.doesNotMatch(svg, /<image|evil/, cover);
      assert.ok(svg.includes('>Bleu Nuit</text>'), cover);
    }
  });

  it('leaves the Spotify card as it was, Spotify being the default', () => {
    for (const spotify of [spotifySvg(), RECENT_SVG, null]) {
      for (const glow of [true, false]) {
        assert.equal(buildCard(PANEL_SVG, spotify, PALETTE.dark, { glow, service: 'spotify' }), buildCard(PANEL_SVG, spotify, PALETTE.dark, { glow }));
      }
    }
    assert.ok(buildCard(PANEL_SVG, spotifySvg(), PALETTE.dark).includes('aria-label="Coding activity and now playing on Spotify"'));
  });
});

describe('the compact Apple Music card', () => {
  const compactApple = (music = appleSvg(), palette = PALETTE.dark) =>
    buildCompactCard(readCompactPanel(COMPACT_PANEL_SVG), music, palette, { glow: palette === PALETTE.dark, service: 'apple' });

  it('draws the strip from the song, the artist and the cover, with no logo', () => {
    const { text, muted } = PALETTE.light;
    const svg = compactApple(appleSvg(), PALETTE.light);
    assert.notEqual(svgInner(svg), null);
    assert.ok(svg.includes('aria-label="Coding activity and last played on Apple Music"'));
    assert.match(svg, /font-size="12" font-weight="700" fill="#53b14f" textLength="[\d.]+" lengthAdjust="spacing">Last played on Apple Music<\/text>/);
    assert.match(svg, new RegExp(`font-size="17" font-weight="700" fill="${text}">Hélène &amp; Les Ondes</text>`));
    assert.match(svg, new RegExp(`font-size="14" fill="${muted}">Bleu Nuit</text>`));
    assert.ok(svg.includes(`clip-path="url(#relay-cover)" href="data:image/jpeg;base64,${RASTERS.jpeg}"/>`));
    assert.equal(svg.split('<image ').length - 1, 1, 'the cover, and no logo');
    assert.equal(svg.split('class="relay-bar"').length - 1, 47);
    assert.doesNotMatch(svg, /foreignObject|<div|upstream|image\/webp|Spotify|Nothing playing/i);
  });

  it('glows in dark mode as the Spotify strip does', () => {
    const dark = compactApple();
    for (const name of ['playing', 'artist', 'bars']) assert.equal(dark.split(`filter="url(#relay-glow-${name})"`).length, 2, name);
    assert.ok(dark.includes('fill="url(#relay-vignette)"'));
  });

  it('says nothing is playing for the error card or an unusable one', () => {
    for (const music of [appleErrorSvg(), appleSvg({ song: '' }), appleSvg({ artist: 'Rock & Roll' }), '', null]) {
      const svg = compactApple(music);
      assert.notEqual(svgInner(svg), null);
      assert.ok(svg.includes(`<g transform="translate(20 -165)">${placeholder(PALETTE.dark)}</g>`));
      assert.doesNotMatch(svg, /Failure|relay-glow|<image/);
    }
  });

  it('draws a tile, not a cover, for a cover that is not a base64 raster', () => {
    for (const cover of ['https://evil.example/c.jpg', 'data:image/png;base64,AAAA', `data:image/webp,${RASTERS.jpeg}`]) {
      const svg = compactApple(appleSvg({ cover }), PALETTE.light);
      assert.ok(svg.includes(`<rect x="14" y="14" width="84" height="84" rx="5" fill="${PALETTE.light.line}"/>`), cover);
      assert.doesNotMatch(svg, /<image|evil/, cover);
    }
  });
});
