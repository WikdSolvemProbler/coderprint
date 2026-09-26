// Pure pieces of the relay: input checks, the cards.json contract, SVG sanitizing and composition.
// Nothing here touches the network, the file system or the environment.

const LOGIN = /^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$/;
const COLOR = /^#[0-9a-fA-F]{6}$/;
const UID = /^[A-Za-z0-9]{1,64}$/;
const PALETTE_KEYS = ['bg', 'text', 'muted', 'line'];

// The generator's sepia and ink themes, used when cards.json carries no valid palette for a mode.
export const DEFAULT_PALETTES = Object.freeze({
  light: Object.freeze({ bg: '#f0e6d2', text: '#3e2b1a', muted: '#6b5848', line: '#d4c4a8' }),
  dark: Object.freeze({ bg: '#100f0e', text: '#f4efe8', muted: '#a7a29b', line: '#35322f' }),
});

// The Spotify widget's own font stack, so the placeholder reads as the same card.
const SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif";

export function isLogin(value) {
  return typeof value === 'string' && LOGIN.test(value);
}

export function isMode(value) {
  return value === 'dark' || value === 'light';
}

export function isAllowed(user, list) {
  if (typeof list !== 'string') return false;
  const wanted = user.toLowerCase();
  return list.split(',').some((name) => name.trim().toLowerCase() === wanted);
}

export function rawUrl(user, file) {
  return `https://raw.githubusercontent.com/${user}/${user}/HEAD/assets/${file}`;
}

export function spotifyUrl(uid, bg) {
  return (
    `https://spotify-github-profile.kittinanx.com/api/view?uid=${uid}&cover_image=true&theme=default` +
    `&show_offline=false&background_color=${bg.slice(1)}&interchange=false&profanity=false&hide_remaster=false`
  );
}

// Returns { palette, uid } or null when the text is not a JSON object. A mode's palette is taken
// only when all four colors are valid: the colors are a designed set, so they are never mixed
// with the defaults.
export function readCards(jsonText, mode) {
  let cards;
  try {
    cards = JSON.parse(jsonText);
  } catch {
    return null;
  }
  if (!isRecord(cards)) return null;
  const given = isRecord(cards.palette) ? cards.palette[mode] : undefined;
  const valid = isRecord(given) && PALETTE_KEYS.every((key) => isColor(given[key]));
  const palette = valid
    ? { bg: given.bg, text: given.text, muted: given.muted, line: given.line }
    : DEFAULT_PALETTES[mode];
  const uid = isRecord(cards.spotify) ? cards.spotify.uid : undefined;
  return { palette, uid: typeof uid === 'string' && UID.test(uid) ? uid : null };
}

function isRecord(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isColor(value) {
  return typeof value === 'string' && COLOR.test(value);
}

// ---------------------------------------------------------------- sanitizing

// Every regex below matches one bounded construct and is driven from a plain loop, so no input
// can make the engine backtrack across a whole document.
const NAME = '[A-Za-z_][\\w.-]*(?::[A-Za-z_][\\w.-]*)?';
const VALUE = `"[^"<]*"|'[^'<]*'`;
const TAG_NAME = new RegExp(`<(${NAME})`, 'y');
const NEXT_ATTRIBUTE = new RegExp(`\\s+(${NAME})\\s*=\\s*(${VALUE})`, 'y');
const TAG_END = /\s*(\/?)>/y;
const CLOSE_TAG = new RegExp(`<\\/(${NAME})\\s*>`, 'y');

// XML allows only the five predefined entities and numeric references without a DTD, and text
// may not contain "]]>".
const BAD_AMPERSAND = /&(?!(?:amp|lt|gt|quot|apos|#[0-9]+|#x[0-9a-fA-F]+);)/;
const BAD_TEXT = /&(?!(?:amp|lt|gt|quot|apos|#[0-9]+|#x[0-9a-fA-F]+);)|\]\]>/;
const ILLEGAL_CHARS = /[\x00-\x08\x0B\x0C\x0E-\x1F\u{FFFE}\u{FFFF}]/u;

// Our composed root declares these, so a fragment may use them without declaring them itself.
const ROOT_PREFIXES = new Set(['xml', 'xmlns', 'xlink']);

// Elements that exist to run code or embed other documents; none belongs in a card.
const DROPPED_ELEMENTS = /^(?:script|iframe|frame|frameset|object|embed)$/i;
const URL_ATTRIBUTES = /^(?:href|src)$/i;
// Links may point inside the document or at an embedded raster; a data: URL of any other type
// (text/html, image/svg+xml) can carry a whole document with no '<' in the source.
const SAFE_URL = /^\s*(?:#|data:image\/(?:png|jpe?g|gif|webp)[;,])/i;
// CSS that can fetch or run something: imports, old script hooks, and any url() that is not a
// fragment or an embedded raster. Checked in <style> text and in every attribute value.
const BAD_CSS = /@import|expression\s*\(|-moz-binding|behavior\s*:|url\(\s*['"]?(?!(?:#|data:image\/(?:png|jpe?g|gif|webp)[;,]))/i;

// Sanitizes an XML fragment in one left to right pass and returns it, or null when the fragment
// is not well formed. Refusing rather than guessing matters: one malformed byte in the composed
// document would stop the whole card from rendering.
export function sanitize(fragment) {
  if (typeof fragment !== 'string' || ILLEGAL_CHARS.test(fragment)) return null;
  const stack = []; // open elements as { name, prefixes }
  let out = '';
  let dropBelow = -1; // stack depth at which a dropped element opened, or -1
  let pos = 0;

  while (pos < fragment.length) {
    const lt = fragment.indexOf('<', pos);
    const text = fragment.slice(pos, lt === -1 ? fragment.length : lt);
    if (BAD_TEXT.test(text)) return null;
    if (insideStyle(stack) && BAD_CSS.test(text)) return null;
    if (dropBelow < 0) out += text;
    if (lt === -1) break;

    if (fragment.startsWith('<!--', lt)) {
      pos = endOf(fragment, '-->', lt + 4);
    } else if (fragment.startsWith('<![CDATA[', lt)) {
      pos = endOf(fragment, ']]>', lt + 9);
      if (pos !== -1 && insideStyle(stack) && BAD_CSS.test(fragment.slice(lt + 9, pos - 3))) return null;
      // As escaped text, so no later step ever has to recognise CDATA.
      if (pos !== -1 && dropBelow < 0) out += escapeText(fragment.slice(lt + 9, pos - 3));
    } else if (fragment.startsWith('<?', lt)) {
      // Dropped: xml-stylesheet can pull in an external style sheet.
      pos = endOf(fragment, '?>', lt + 2);
    } else if (fragment.startsWith('</', lt)) {
      CLOSE_TAG.lastIndex = lt;
      const close = CLOSE_TAG.exec(fragment);
      if (!close || stack.length === 0 || stack.pop().name !== close[1]) return null;
      if (dropBelow < 0) out += `</${close[1]}>`;
      else if (stack.length === dropBelow) dropBelow = -1;
      pos = CLOSE_TAG.lastIndex;
    } else {
      const tag = readOpenTag(fragment, lt);
      if (!tag) return null;
      const inherited = stack.length ? stack[stack.length - 1].prefixes : ROOT_PREFIXES;
      const element = checkElement(tag, inherited);
      if (!element) return null;
      const dropped = dropBelow >= 0 || DROPPED_ELEMENTS.test(localName(tag.name));
      if (!dropped) out += `<${tag.name}${element.attributes}${tag.selfClosing ? '/>' : '>'}`;
      if (!tag.selfClosing) {
        if (dropped && dropBelow < 0) dropBelow = stack.length;
        stack.push({ name: tag.name, prefixes: element.prefixes });
      }
      pos = tag.end;
    }
    if (pos === -1) return null;
  }
  return stack.length === 0 ? out : null;
}

// Returns the index just past the terminator, or -1 when the construct never ends.
function endOf(text, terminator, from) {
  const at = text.indexOf(terminator, from);
  return at === -1 ? -1 : at + terminator.length;
}

// Reads the open tag at pos as { name, attributes, selfClosing, end }, or returns null.
function readOpenTag(text, pos) {
  TAG_NAME.lastIndex = pos;
  const head = TAG_NAME.exec(text);
  if (!head) return null;
  const attributes = [];
  let at = TAG_NAME.lastIndex;
  for (;;) {
    NEXT_ATTRIBUTE.lastIndex = at;
    const attribute = NEXT_ATTRIBUTE.exec(text);
    if (!attribute) break;
    attributes.push({ name: attribute[1], quoted: attribute[2], value: attribute[2].slice(1, -1) });
    at = NEXT_ATTRIBUTE.lastIndex;
  }
  TAG_END.lastIndex = at;
  const tail = TAG_END.exec(text);
  if (!tail) return null;
  return { name: head[1], attributes, selfClosing: tail[1] === '/', end: TAG_END.lastIndex };
}

// Checks one open tag against XML's rules and returns { attributes, prefixes }, with unsafe
// attributes left out of the markup, or null when the tag is not well formed.
function checkElement(tag, inherited) {
  // A tag's own declarations count for the tag itself, whatever order its attributes come in.
  const declared = tag.attributes.filter((a) => a.name.startsWith('xmlns:')).map((a) => a.name.slice(6));
  const prefixes = declared.length ? new Set([...inherited, ...declared]) : inherited;
  if (!inScope(tag.name, prefixes)) return null;

  const seen = new Set();
  let attributes = '';
  for (const { name, quoted, value } of tag.attributes) {
    if (seen.has(name) || BAD_AMPERSAND.test(value) || !inScope(name, prefixes)) return null;
    seen.add(name);
    if (isSafeAttribute(name, value)) attributes += ` ${name}=${quoted}`;
  }
  return { attributes, prefixes };
}

// An undeclared prefix would make the composed document fail to parse.
function inScope(name, prefixes) {
  const colon = name.indexOf(':');
  return colon === -1 || prefixes.has(name.slice(0, colon));
}

function isSafeAttribute(name, value) {
  if (name === 'xmlns' || name.startsWith('xmlns:')) return true;
  const local = localName(name);
  // srcset can list several URLs, so a check on its start proves nothing.
  if (/^on/i.test(local) || /^srcset$/i.test(local)) return false;
  if (URL_ATTRIBUTES.test(local)) return SAFE_URL.test(value);
  // An SVG animation can write a link or an event handler after load, so it may not target one.
  // No attribute name needs a character reference, and one could spell "href" past the check.
  if (local === 'attributeName') {
    if (value.includes('&')) return false;
    const target = localName(value.trim());
    return !/^on/i.test(target) && !URL_ATTRIBUTES.test(target);
  }
  // style, fill, stroke, filter, mask, clip-path and marker-* can all hold a url(); none may reach out.
  return !BAD_CSS.test(value);
}

function localName(name) {
  return name.slice(name.indexOf(':') + 1);
}

function insideStyle(stack) {
  return stack.length > 0 && localName(stack[stack.length - 1].name).toLowerCase() === 'style';
}

function escapeText(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ---------------------------------------------------------------- composition

const SPACE = /\s*/y;
const DOCTYPE = /<!DOCTYPE[^[>]*(?:\[[^\]]*\])?\s*>/y;
const ROOT_CLOSE = /^<\/svg\s*>$/;

// Returns the sanitized markup between the root <svg ...> tag and its closing tag, or null when
// the text is not an SVG document.
export function svgInner(text) {
  if (typeof text !== 'string') return null;
  const start = prologEnd(text);
  const root = start === -1 ? null : readOpenTag(text, start);
  if (!root || root.name !== 'svg' || root.selfClosing) return null;
  const end = text.trimEnd();
  const close = end.lastIndexOf('</svg');
  if (close < root.end || !ROOT_CLOSE.test(end.slice(close))) return null;
  return sanitize(text.slice(root.end, close));
}

// Skips what may come before the root element: a byte order mark, whitespace, processing
// instructions, comments and a doctype. Returns -1 when one of them never ends.
function prologEnd(text) {
  let pos = text.charCodeAt(0) === 0xfeff ? 1 : 0;
  for (;;) {
    SPACE.lastIndex = pos;
    SPACE.test(text);
    pos = SPACE.lastIndex;
    if (text.startsWith('<?', pos)) {
      pos = endOf(text, '?>', pos + 2);
    } else if (text.startsWith('<!--', pos)) {
      pos = endOf(text, '-->', pos + 4);
    } else if (text.startsWith('<!DOCTYPE', pos)) {
      DOCTYPE.lastIndex = pos;
      pos = DOCTYPE.test(text) ? DOCTYPE.lastIndex : -1;
    } else {
      return pos;
    }
    if (pos === -1) return -1;
  }
}

// WebKit (Safari, and the GitHub app, which is built on it) draws absolutely positioned or
// opacity-animated HTML inside an SVG foreignObject at its unscaled size and in the wrong place,
// so the widget's equalizer bars sprawled across the whole card on phones. Here they sit in an
// ordinary row that ends where they did, on the cover's top edge, and only their height moves.
export const BAR_RULES =
  '#bars{position:static!important;display:flex!important;align-items:flex-end;gap:1px;' +
  'width:auto!important;height:22px!important;margin:-22px 0 0!important;overflow:hidden}' +
  '.bar{position:static!important;flex:0 0 3px;opacity:1!important;animation-name:cpbar!important}' +
  '@keyframes cpbar{from{height:3px}to{height:22px}}';

// Dark mode's glow, matching the panel's: the green header and the equalizer bloom and the artist
// carries a soft halo. Shadows only, which WebKit draws in place inside a foreignObject.
export const GLOW_RULES =
  '.playing{text-shadow:0 0 6px rgba(83,177,79,.5)}' +
  '.artist{text-shadow:0 0 8px rgba(255,255,255,.14)}' +
  '.bar{box-shadow:0 0 4px rgba(83,177,79,.45)}';

// Lets the Spotify card sit on the panel's background in the panel's colors. The rules go at the
// end of the widget's own style sheet so that they win.
export function recolor(inner, { text, muted }, glow = false) {
  const rules =
    '.container{background:transparent!important}' +
    `.artist{color:${text}!important}.song{color:${muted}!important}` +
    BAR_RULES +
    (glow ? GLOW_RULES : '');
  // After sanitize there is no CDATA, and neither text nor attribute values can hold "<", so the
  // first literal </style> is the first real closing tag.
  const at = inner.indexOf('</style>');
  return at === -1 ? `<style>${rules}</style>${inner}` : inner.slice(0, at) + rules + inner.slice(at);
}

// The right pane when nothing live can be shown: the widget's equalizer at rest above a quiet
// line, so the card keeps its shape and still reads as a music card.
export function placeholder({ muted }) {
  const bars = [0, 1, 2, 3, 4]
    .map((i) => `<rect x="${150.5 + 4 * i}" y="207" width="3" height="3" rx="1" fill="${muted}" fill-opacity=".45"/>`)
    .join('');
  return (
    bars +
    `<text x="160" y="235" text-anchor="middle" font-family="${SANS}" font-size="14" fill="${muted}">` +
    'Nothing playing</text>'
  );
}

// In dark mode the panel's corners fall away under a vignette; the right pane gets its own, so the two
// darken alike where they meet.
const RIGHT_VIGNETTE =
  '<defs><radialGradient id="vignetteRight" cx="50%" cy="48%" r="75%"><stop offset=".62" stop-color="#000" ' +
  'stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".22"/></radialGradient></defs>' +
  '<rect x="560" width="336" height="445" rx="10" fill="url(#vignetteRight)"/>';

export function compose(panelInner, rightInner, { bg, line }, glow = false) {
  return (
    '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="896" height="445" ' +
    'viewBox="0 0 896 445" role="img" aria-label="Coding activity and now playing on Spotify">' +
    `<rect width="896" height="445" rx="10" fill="${bg}"/>` +
    `<svg x="0" y="0" width="576" height="445" viewBox="0 0 576 445">${panelInner}</svg>` +
    `<rect x="560" width="336" height="445" rx="10" fill="${bg}"/>` +
    '<rect x="560" width="336" height="445" rx="10" fill="url(#grid)"/>' +
    `<line x1="576" y1="16" x2="576" y2="429" stroke="${line}"/>` +
    `<svg x="576" y="0" width="320" height="445" viewBox="0 0 320 445">${rightInner}</svg>` +
    (glow ? RIGHT_VIGNETTE : '') +
    '</svg>'
  );
}

// Returns the finished card, or null when the panel is unusable. A missing or unusable Spotify
// card is not an error: the placeholder takes its place. glow is dark mode's.
export function buildCard(panelText, spotifyText, palette, { glow = false } = {}) {
  const panel = svgInner(panelText);
  if (panel === null) return null;
  const spotify = svgInner(spotifyText);
  const right = spotify === null ? placeholder(palette) : recolor(spotify, palette, glow);
  return compose(panel, right, palette, glow);
}
