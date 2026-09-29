import assert from 'node:assert/strict';
import { test } from 'node:test';
import fc from 'fast-check';
import { sanitize, readCards, DEFAULT_PALETTES } from '../../lib/compose.js';
import { fuzz as fuzzSvg } from './svg.mjs';
import { fuzz as fuzzCards } from './cards.mjs';

const safeText = fc.array(fc.constantFrom('a', 'Z', '0', ' ', '&', '<', '>', '"', "'", '\n', 'é'), { maxLength: 80 })
  .map((chars) => chars.join(''));
const escapeXml = (text) => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const hex = fc.array(fc.constantFrom(...'0123456789abcdefABCDEF'), { minLength: 6, maxLength: 6 })
  .map((digits) => `#${digits.join('')}`);
const maybeColor = fc.oneof(hex, fc.string({ maxLength: 16 }));
const palette = fc.record({ bg: maybeColor, text: maybeColor, muted: maybeColor, line: maybeColor });
const colorPattern = /^#[0-9a-fA-F]{6}$/;
const spotifyPattern = /^[A-Za-z0-9._-]{1,64}$/;
const applePattern = /^[A-Za-z0-9.]{1,64}$/;

test('unsafe SVG event and URL attributes are removed while text survives', () => {
  fc.assert(fc.property(
    safeText,
    fc.constantFrom('onload', 'onerror', 'onclick', 'onLoad'),
    fc.constantFrom('javascript:alert(1)', 'https://attacker.invalid/x', '//attacker.invalid/x', 'data:text/html,evil'),
    (text, event, url) => {
      const escaped = escapeXml(text);
      const input = `<g ${event}="alert(1)" href="${url}"><text>${escaped}</text></g>`;
      assert.equal(sanitize(input), `<g><text>${escaped}</text></g>`);
    },
  ), { numRuns: 350 });
});

test('JSON settings only expose complete colors and validated music IDs', () => {
  fc.assert(fc.property(
    palette,
    fc.string({ maxLength: 80 }),
    fc.string({ maxLength: 80 }),
    (colors, spotify, apple) => {
      const json = JSON.stringify({ presentation: { palette: { light: colors }, spotify: { uid: spotify }, apple_music: { uid: apple } } });
      const uid = spotifyPattern.test(spotify) ? spotify : null;
      const expected = {
        palette: Object.values(colors).every((value) => colorPattern.test(value)) ? { ...colors } : DEFAULT_PALETTES.light,
        uid,
        apple: uid === null && applePattern.test(apple) ? apple : null,
      };
      assert.deepEqual(readCards(json, 'light'), expected);
    },
  ), { numRuns: 350 });
});

test('shrinkable raw bytes preserve SVG and JSON parser invariants', () => {
  fc.assert(fc.property(fc.uint8Array({ maxLength: 512 }), (bytes) => {
    const data = Buffer.from(bytes);
    fuzzSvg(data);
    fuzzCards(data);
  }), { numRuns: 300 });
});
