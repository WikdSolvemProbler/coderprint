import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  DEFAULT_PALETTES,
  buildCard,
  compose,
  isAllowed,
  isLogin,
  isMode,
  placeholder,
  rawUrl,
  readCards,
  recolor,
  sanitize,
  spotifyUrl,
  svgInner,
} from '../lib/compose.js';
import { PALETTE, PANEL_SVG, PIXEL, cardsJson, spotifySvg } from './fixtures.js';

const RULES_DARK =
  '.container{background:transparent!important}' +
  `.artist{color:${PALETTE.dark.text}!important}.song{color:${PALETTE.dark.muted}!important}` +
  '#bars{position:static!important;display:flex!important;align-items:flex-end;gap:1px;' +
  'width:auto!important;height:22px!important;margin:-22px 0 0!important;overflow:hidden}' +
  '.bar{position:static!important;flex:0 0 3px;opacity:1!important;animation-name:cpbar!important}' +
  '@keyframes cpbar{from{height:3px}to{height:22px}}';

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
});

describe('readCards', () => {
  it('takes a valid palette and uid', () => {
    assert.deepEqual(readCards(cardsJson(), 'dark'), { palette: PALETTE.dark, uid: '1joahg6umn39flaqsl1c3j9n3' });
    assert.deepEqual(readCards(cardsJson(), 'light').palette, PALETTE.light);
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
