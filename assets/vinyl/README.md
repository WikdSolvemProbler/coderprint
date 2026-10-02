# Vinyl record texture

`record-ridges.png` is the edited bitmap based on the two vinyl reference images supplied by the project owner. The built-in imagegen tool enhanced the rounded ridges and removed the white background and album label, keeping transparency. The final prompt is in `record-ridges.prompt.txt`.

`record-ridges.webp` packages the same bitmap at quality 95 with the alpha preserved. `lib/vinyl-texture.js` embeds those exact WebP bytes so the composed card requires no additional image request or runtime file access. Both music providers use this asset; their current artwork replaces the center label.

The renderer normalizes the opaque disc bounds to its circular slot. The texture turns gently by two degrees with a six-percent brightness change, while the album label rotates independently. Both animations are disabled for reduced-motion preferences.
