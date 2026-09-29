import assert from 'node:assert/strict';
import { readCards, spotifyUrl } from '../../lib/compose.js';

const color = /^#[0-9a-fA-F]{6}$/;
const spotifyId = /^[A-Za-z0-9._-]{1,64}$/;
const appleId = /^[A-Za-z0-9.]{1,64}$/;

function check(result) {
  if (result === null) return;
  assert.deepEqual(Object.keys(result).sort(), ['apple', 'palette', 'uid']);
  assert.deepEqual(Object.keys(result.palette).sort(), ['bg', 'line', 'muted', 'text']);
  for (const value of Object.values(result.palette)) assert.match(value, color);
  if (result.uid !== null) {
    assert.match(result.uid, spotifyId);
    assert.equal(result.apple, null, 'both music services selected');
    assert.ok(spotifyUrl(result.uid, result.palette.bg).startsWith('https://spotify-github-profile.kittinanx.com/api/view?'));
  }
  if (result.apple !== null) assert.match(result.apple, appleId);
}

export function fuzz(data) {
  const input = data.toString('utf8');
  for (const mode of ['light', 'dark']) check(readCards(input, mode));

  // Keep reaching the schema validation even when byte mutation breaks JSON syntax.
  const structured = JSON.stringify({
    presentation: {
      palette: { light: { bg: input, text: input, muted: input, line: input } },
      spotify: { uid: input },
      apple_music: { uid: input },
    },
  });
  check(readCards(structured, 'light'));
}
