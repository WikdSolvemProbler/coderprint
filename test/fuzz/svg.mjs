import assert from 'node:assert/strict';
import { sanitize, svgInner, readCompactPanel, buildCard, DEFAULT_PALETTES } from '../../lib/compose.js';

// Jazzer.js instruments compose.js and mutates the corpus as raw UTF-8 SVG/XML input.
// The round trips catch broken XML, unstable rewriting, and unsafe attribute retention.
export function fuzz(data) {
  const input = data.toString('utf8');
  const fragment = sanitize(input);
  if (fragment !== null) {
    assert.equal(sanitize(fragment), fragment, 'sanitizing twice changed accepted markup');
    assert.equal(svgInner(`<svg>${fragment}</svg>`), fragment, 'accepted fragment cannot survive an SVG document');

    const hostile = `<g onload="alert(1)" href="javascript:alert(1)">${fragment}</g>`;
    assert.equal(sanitize(hostile), `<g>${fragment}</g>`, 'event or external URL attribute survived');
  }

  const panel = svgInner(input);
  if (panel !== null) {
    assert.equal(sanitize(panel), panel, 'SVG inner markup is not sanitized');
    const card = buildCard(input, '<svg><script>alert(1)</script></svg>', DEFAULT_PALETTES.light);
    assert.notEqual(card, null, 'accepted SVG panel did not compose');
    assert.notEqual(svgInner(card), null, 'composed card is not a usable SVG');
  }
  readCompactPanel(input);
}
