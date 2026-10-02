# Vinyl record texture

`record-ridges.png` is the edited bitmap based on the two vinyl reference images supplied by the project owner. The built-in imagegen tool enhanced the rounded ridges and removed the white background and album label, keeping transparency. The final prompt is in `record-ridges.prompt.txt`.

`record-ridges.webp` preserves that first edited reference. Its studio highlights are baked into the pixels, so it is not the rotating material.

`record-material.png` is a second built-in imagegen edit of that reference: even diffuse illumination replaces the directional highlights while retaining broad ridges and surface grain. The exact prompt is in `record-material.prompt.txt`. `record-material.webp` packages this material at quality 95 with alpha preserved. `lib/vinyl-texture.js` embeds its exact WebP bytes, requiring no additional request or runtime file access.

The material and current album art rotate in one SVG group. Separate soft light lobes stay in screen space, with a subtle two-degree shift and six-percent intensity change. A luminance mask reuses the same rotating material to make the light respond to the ridges and grain; an annular clip excludes the label. All motion is disabled for reduced-motion preferences.

This separation follows [SongArt's rotating-material and stationary-light implementation](https://github.com/sansoo1972/songart/blob/d2f4798c4ee9809a7342252822f651170a0f61b4/src/display.rs). No SongArt code, assets or runtime dependencies are included. SVG transform origins use the fixed `0 0 100 100` view box, following [MDN's transform-origin documentation](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/transform-origin).
