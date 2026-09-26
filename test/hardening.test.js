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
