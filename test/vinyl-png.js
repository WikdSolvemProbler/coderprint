import assert from 'node:assert/strict';
import { inflateSync } from 'node:zlib';

// Read only the bounded, non-interlaced RGBA8 source format used by our texture.
export function readPngAlpha(bytes) {
  assert.ok(bytes.length <= 8 * 1024 * 1024, 'bounded PNG input');
  assert.equal(bytes.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
  let width;
  let height;
  const data = [];
  let ended = false;
  for (let offset = 8; offset < bytes.length;) {
    assert.ok(offset + 12 <= bytes.length, 'complete PNG chunk');
    const length = bytes.readUInt32BE(offset);
    const type = bytes.toString('ascii', offset + 4, offset + 8);
    assert.ok(length <= bytes.length - offset - 12, 'bounded PNG chunk');
    const chunk = bytes.subarray(offset + 8, offset + 8 + length);
    if (type === 'IHDR') {
      assert.equal(offset, 8);
      assert.equal(length, 13);
      width = chunk.readUInt32BE(0);
      height = chunk.readUInt32BE(4);
      assert.ok(width > 0 && height > 0 && width <= 2048 && height <= 2048);
      assert.deepEqual([...chunk.subarray(8)], [8, 6, 0, 0, 0], 'RGBA8 without interlacing');
    } else if (type === 'IDAT') {
      assert.ok(width && height, 'header precedes image data');
      data.push(chunk);
    } else if (type === 'IEND') {
      assert.equal(length, 0);
      assert.equal(offset + 12, bytes.length);
      ended = true;
    }
    offset += length + 12;
  }
  assert.ok(ended && data.length, 'complete PNG image');
  const stride = width * 4;
  const expected = (stride + 1) * height;
  const raw = inflateSync(Buffer.concat(data), { maxOutputLength: expected });
  assert.equal(raw.length, expected);
  const alpha = new Uint8Array(width * height);
  let previous = Buffer.alloc(stride);
  let row = Buffer.alloc(stride);
  for (let y = 0; y < height; y += 1) {
    const start = y * (stride + 1);
    const filter = raw[start];
    assert.ok(filter <= 4, 'supported PNG row filter');
    for (let x = 0; x < stride; x += 1) {
      const left = x >= 4 ? row[x - 4] : 0;
      const up = previous[x];
      const corner = x >= 4 ? previous[x - 4] : 0;
      let prediction = 0;
      if (filter === 1) prediction = left;
      if (filter === 2) prediction = up;
      if (filter === 3) prediction = Math.floor((left + up) / 2);
      if (filter === 4) {
        const p = left + up - corner;
        const a = Math.abs(p - left), b = Math.abs(p - up), c = Math.abs(p - corner);
        prediction = a <= b && a <= c ? left : b <= c ? up : corner;
      }
      row[x] = (raw[start + 1 + x] + prediction) & 255;
    }
    for (let x = 0; x < width; x += 1) alpha[y * width + x] = row[x * 4 + 3];
    [previous, row] = [row, previous];
  }
  return { width, height, alpha };
}

// Exterior transparency touches the bitmap edge; the label opening does not.
export function enclosedOpening({ width, height, alpha }) {
  const seen = new Uint8Array(alpha.length);
  const queue = new Int32Array(alpha.length);
  let largest;
  for (let seed = 0; seed < alpha.length; seed += 1) {
    if (alpha[seed] !== 0 || seen[seed]) continue;
    let head = 0, tail = 1;
    queue[0] = seed;
    seen[seed] = 1;
    let minX = width, minY = height, maxX = -1, maxY = -1, exterior = false;
    while (head < tail) {
      const index = queue[head++];
      const x = index % width, y = Math.floor(index / width);
      minX = Math.min(minX, x); maxX = Math.max(maxX, x);
      minY = Math.min(minY, y); maxY = Math.max(maxY, y);
      if (x === 0 || y === 0 || x === width - 1 || y === height - 1) exterior = true;
      for (const next of [x > 0 ? index - 1 : -1, x + 1 < width ? index + 1 : -1,
        y > 0 ? index - width : -1, y + 1 < height ? index + width : -1]) {
        if (next >= 0 && alpha[next] === 0 && !seen[next]) {
          seen[next] = 1;
          queue[tail++] = next;
        }
      }
    }
    if (!exterior && (!largest || tail > largest.pixels)) {
      largest = { cx: (minX + maxX) / 2, cy: (minY + maxY) / 2, pixels: tail };
    }
  }
  assert.ok(largest, 'the texture contains an enclosed transparent label opening');
  return largest;
}
