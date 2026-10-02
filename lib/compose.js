import { VINYL_TEXTURE } from './vinyl-texture.js';

// Pure pieces of the relay: input checks, the cards.json contract, SVG sanitizing and composition.
// Nothing here touches the network, the file system or the environment.

const LOGIN = /^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$/;
const COLOR = /^#[0-9a-fA-F]{6}$/;
// Spotify user ids: the random ones given today, and older accounts' user names, which may hold dots,
// underscores and hyphens, all safe in a query string as they are; settings() in coderprint.py takes the same.
const UID = /^[A-Za-z0-9._-]{1,64}$/;
// Apple Music's uids are Sign in with Apple's user ids, digits and hex in three parts joined by dots.
const APPLE_UID = /^[A-Za-z0-9.]{1,64}$/;
const PALETTE_KEYS = ['bg', 'text', 'muted', 'line'];

// The generator's plain look (PLAIN in coderprint.py), the fallback when cards.json carries no valid palette
// for a mode. The relay holds none of the design's themes: they live in design/, licensed apart from the code.
export const DEFAULT_PALETTES = Object.freeze({
  light: Object.freeze({ bg: '#ffffff', text: '#1f2328', muted: '#59636e', line: '#d0d7de' }),
  dark: Object.freeze({ bg: '#010409', text: '#e6edf3', muted: '#9198a1', line: '#30363d' }),
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

// The card of rayriffy/apple-music-github-profile's hosted service, which takes nothing but the theme and
// the uid. The relay passes none of it on: it reads the track from it and draws a card of its own (see
// musicPane).
export function appleUrl(uid, mode) {
  return `https://music-profile.rayriffy.com/theme/${mode}.svg?uid=${encodeURIComponent(uid)}`;
}

// Returns { palette, uid, apple } or null when the text is not a JSON object. A mode's palette is taken
// only when all four colors are valid: the colors are a designed set, so they are never mixed
// with the defaults. uid is the Spotify widget's and apple the Apple Music card's, each null when
// cards.json names no valid one. The generator names at most one; a file naming both gets Spotify, as
// it did before Apple Music was offered.
export function readCards(jsonText, mode) {
  let parsed;
  try {
    parsed = JSON.parse(jsonText);
  } catch {
    return null;
  }
  if (!isRecord(parsed)) return null;
  // coderprint.json keeps what the relay reads under presentation; cards.json, which it replaced, at its top
  const cards = isRecord(parsed.presentation) ? parsed.presentation : parsed;
  const given = isRecord(cards.palette) ? cards.palette[mode] : undefined;
  const valid = isRecord(given) && PALETTE_KEYS.every((key) => isColor(given[key]));
  const palette = valid
    ? { bg: given.bg, text: given.text, muted: given.muted, line: given.line }
    : DEFAULT_PALETTES[mode];
  const spotify = isRecord(cards.spotify) ? cards.spotify.uid : undefined;
  const uid = typeof spotify === 'string' && UID.test(spotify) ? spotify : null;
  const named = isRecord(cards.apple_music) ? cards.apple_music.uid : undefined;
  const apple = uid === null && typeof named === 'string' && APPLE_UID.test(named) ? named : null;
  return { palette, uid, apple };
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

// Without a DTD, XML allows only the five predefined entities and numeric references to characters
// it allows (see badReferences), and text may not contain "]]>". A character XML does not allow may
// not be written either, and neither may half of a surrogate pair, which is no character at all.
const REFERENCE = /&(?:amp|lt|gt|quot|apos|#([0-9]+)|#x([0-9a-fA-F]+));/y;
const ILLEGAL_CHARS = /[\x00-\x08\x0B\x0C\x0E-\x1F￾￿\uD800-\uDFFF]/u;

const XML_NS = 'http://www.w3.org/XML/1998/namespace';
const XMLNS_NS = 'http://www.w3.org/2000/xmlns/';
// The prefixes in scope where a fragment starts, with their namespaces: xml is bound in every document
// and our composed root binds xlink, so a fragment may use both without declaring them.
const ROOT_PREFIXES = new Map([['xml', XML_NS], ['xlink', 'http://www.w3.org/1999/xlink']]);
// A namespace name Chrome's parser reads as a URI: a scheme, then an authority of plain host characters
// and an optional port followed by a path of whole segments, or a path that does not start with "//",
// then an optional query and fragment, every character one RFC 3986 allows there or a %-escape. Chrome
// refuses a document binding any other (white space, a non-ASCII letter, "{", "|", a stray "%", a
// port that is not a number, or one past 2147483647), even where Namespaces in XML does not, and the card
// then draws nothing. A port here is at most five digits, since no real port is longer. Every real card
// binds only the SVG and XHTML namespaces, with no port and no relative name.
const PCHAR = "(?:[A-Za-z0-9._~!$&'()*+,;=:@-]|%[0-9A-Fa-f]{2})";
const NAMESPACE_URI = new RegExp(
  `^[A-Za-z][A-Za-z0-9+.-]*:(?:\\/\\/[A-Za-z0-9.-]*(?::[0-9]{1,5})?(?:\\/${PCHAR}*)*|(?!\\/\\/)(?:${PCHAR}|\\/)*)` +
    `(?:\\?(?:${PCHAR}|[/?])*)?(?:#(?:${PCHAR}|[/?])*)?$`,
);
// The deepest a fragment's markup may nest. A card sets it two levels down, and the recently played
// equalizer can add one more, so a card nests at most 253 deep: far within the 5000 past which Chrome was
// measured to draw nothing, and under 256, which is believed, not measured, to be libxml2's default limit
// for parsers that set one. Real cards nest 7 deep.
const MAX_DEPTH = 250;

// Elements that exist to run code or embed other documents, or, as a meta refresh inside a
// foreignObject does, send the viewer elsewhere; none belongs in a card.
const DROPPED_ELEMENTS = /^(?:script|iframe|frame|frameset|object|embed|meta)$/i;
// Every attribute that names one URL the viewer may fetch or go to: href and xlink:href, src, poster,
// background, and a form's action and formaction; then lowsrc, dynsrc, manifest, and data and codebase
// (object's, applet's), which older engines fetch. Each may keep only a fragment or an embedded raster.
const URL_ATTRIBUTES = /^(?:href|src|poster|background|action|formaction|lowsrc|dynsrc|manifest|data|codebase)$/i;
// Attributes that list URLs or send one elsewhere as a side effect, so a check on the value's start
// proves nothing: srcset (img, source), imagesrcset (a link rel=preload as=image fetches it), ping (a
// followed link reports to every URL it lists) and attributionsrc (fetched where Chrome's attribution
// reporting is on, which resolves even "#x" to the card's own address). No card needs any of them.
const DROPPED_ATTRIBUTES = /^(?:srcset|imagesrcset|ping|attributionsrc)$/i;
// Links may point inside the document or at an embedded raster; a data: URL of any other type
// (text/html, image/svg+xml) can carry a whole document with no '<' in the source.
const SAFE_URL = /^\s*(?:#|data:image\/(?:png|jpe?g|gif|webp)[;,])/i;
// CSS that can fetch or run something: imports, old script hooks, image-set(), which fetches whatever
// it lists, src() and image(), which the CSS specifications define to fetch a URL (no browser draws them
// yet), and any url() that is not a fragment or an embedded raster. Checked in <style> text and in every
// attribute value (see badCss).
const BAD_CSS = new RegExp(
  [
    /@import|expression\s*\(|-moz-binding|behavior\s*:|(?:-webkit-)?image-set|\b(?:src|image)\s*\(/.source,
    /url\(\s*['"]?(?!(?:#|data:image\/(?:png|jpe?g|gif|webp)[;,]))/.source,
  ].join('|'),
  'i',
);

// Sanitizes an XML fragment in one left to right pass and returns it, or null when the fragment
// is not well formed. Refusing rather than guessing matters: one malformed byte in the composed
// document would stop the whole card from rendering.
//
// A style element's CSS is checked whole, as it is written out, at its closing tag. Checking it a piece
// at a time is not enough: a comment, processing instruction or element dropped between two pieces
// joins them in the output, so "@imp<!-- -->ort" is written as "@import". For the same reason a style
// element may hold nothing but text and CDATA: anything else refuses the fragment. Text is joined the
// same way: "]]<!-- -->>" would be written as "]]>", which XML does not allow in text, so the text
// written out since the last tag is checked across every seam.
export function sanitize(fragment) {
  return clean(fragment)?.markup ?? null;
}

// sanitize's pass, returning { markup, depth }, depth being how deep the markup's elements nest.
function clean(fragment) {
  if (typeof fragment !== 'string' || ILLEGAL_CHARS.test(fragment)) return null;
  const stack = []; // open elements as { name, prefixes }
  let out = '';
  let dropBelow = -1; // stack depth at which a dropped element opened, or -1
  let pos = 0;
  let css = ''; // the style element open now, as it is written out: its text, and its CDATA escaped
  let tail = ''; // the last two characters of the text written out since the last tag
  let depth = 0;
  // Writes text out, or returns false when it would complete a "]]>" begun before it. The text itself
  // never holds one: text holding it is refused and CDATA is written with ">" escaped.
  const write = (piece) => {
    if ((tail + piece.slice(0, 2)).includes(']]>')) return false;
    tail = piece.length >= 2 ? piece.slice(-2) : (tail + piece).slice(-2);
    out += piece;
    return true;
  };

  while (pos < fragment.length) {
    const lt = fragment.indexOf('<', pos);
    const text = fragment.slice(pos, lt === -1 ? fragment.length : lt);
    if (text.includes(']]>') || badReferences(text)) return null;
    if (dropBelow < 0 && !write(text)) return null;
    if (lt === -1) break;

    const inStyle = insideStyle(stack);
    if (inStyle) {
      css += text;
      if (!fragment.startsWith('<![CDATA[', lt) && !fragment.startsWith('</', lt)) return null;
    }
    if (fragment.startsWith('<!--', lt)) {
      pos = endOf(fragment, '-->', lt + 4);
    } else if (fragment.startsWith('<![CDATA[', lt)) {
      pos = endOf(fragment, ']]>', lt + 9);
      // As escaped text, so no later step ever has to recognise CDATA.
      const data = pos === -1 ? '' : escapeText(fragment.slice(lt + 9, pos - 3));
      if (inStyle) css += data;
      if (dropBelow < 0 && !write(data)) return null;
    } else if (fragment.startsWith('<?', lt)) {
      // Dropped: xml-stylesheet can pull in an external style sheet.
      pos = endOf(fragment, '?>', lt + 2);
    } else if (fragment.startsWith('</', lt)) {
      if (inStyle && badCss(css)) return null;
      css = '';
      CLOSE_TAG.lastIndex = lt;
      const close = CLOSE_TAG.exec(fragment);
      if (!close || stack.length === 0 || stack.pop().name !== close[1]) return null;
      if (dropBelow < 0) {
        out += `</${close[1]}>`;
        tail = '';
      } else if (stack.length === dropBelow) dropBelow = -1;
      pos = CLOSE_TAG.lastIndex;
    } else {
      const tag = readOpenTag(fragment, lt);
      if (!tag) return null;
      const inherited = stack.length ? stack[stack.length - 1].prefixes : ROOT_PREFIXES;
      const element = checkElement(tag, inherited);
      if (!element) return null;
      const dropped = dropBelow >= 0 || DROPPED_ELEMENTS.test(localName(tag.name));
      if (!dropped) {
        out += `<${tag.name}${element.attributes}${tag.selfClosing ? '/>' : '>'}`;
        tail = '';
        // Every element open is written out, since nothing is written below a dropped one.
        depth = Math.max(depth, stack.length + 1);
      }
      if (!tag.selfClosing) {
        if (dropped && dropBelow < 0) dropBelow = stack.length;
        stack.push({ name: tag.name, prefixes: element.prefixes });
      }
      pos = tag.end;
    }
    if (pos === -1) return null;
  }
  return stack.length === 0 ? { markup: out, depth } : null;
}

// Whether text, or an attribute value, holds an "&" that starts no reference XML allows: one of the
// five predefined entities, or a numeric reference to a character XML allows. "&#0;", "&#x1B;",
// "&#xFFFE;", "&#xD800;" and "&#x110000;" are as fatal to a parser as the characters themselves.
function badReferences(text) {
  for (let at = text.indexOf('&'); at !== -1; at = text.indexOf('&', at + 1)) {
    REFERENCE.lastIndex = at;
    const reference = REFERENCE.exec(text);
    if (!reference) return true;
    const [, decimal, hex] = reference;
    if ((decimal || hex) && !isXmlChar(decimal ? Number(decimal) : parseInt(hex, 16))) return true;
  }
  return false;
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

// Checks one open tag against the rules of XML and of Namespaces in XML and returns { attributes,
// prefixes }, with unsafe attributes left out of the markup and prefixes mapping each prefix in scope to
// its namespace, or null when the tag is not well formed.
function checkElement(tag, inherited) {
  // Chrome refuses xml as an element prefix, even when bound to XML_NS. xml:* attributes remain valid.
  if (tag.name.startsWith('xml:')) return null;
  for (const { value } of tag.attributes) if (badReferences(value)) return null;
  // A tag's own declarations count for the tag itself, whatever order its attributes come in.
  let prefixes = inherited;
  for (const { name, value } of tag.attributes) {
    if (!isDeclaration(name)) continue;
    const prefix = name === 'xmlns' ? null : name.slice(6);
    const uri = attributeText(value);
    if (!isBinding(prefix, uri)) return null;
    if (prefix === null) continue;
    if (prefixes === inherited) prefixes = new Map(inherited);
    prefixes.set(prefix, uri);
  }
  if (expandedName(tag.name, prefixes) === null) return null;

  // No two attributes may share a name once their prefixes are read: a:href and xlink:href are one
  // attribute when a and xlink name the same namespace.
  const seen = new Set();
  let attributes = '';
  for (const { name, quoted, value } of tag.attributes) {
    const expanded = isDeclaration(name) ? name : expandedName(name, prefixes);
    if (expanded === null || seen.has(expanded)) return null;
    seen.add(expanded);
    if (isSafeAttribute(name, value)) attributes += ` ${name}=${quoted}`;
  }
  return { attributes, prefixes };
}

function isDeclaration(name) {
  return name === 'xmlns' || name.startsWith('xmlns:');
}

// Whether a declaration may bind prefix (null for the default namespace) to uri. Namespaces in XML
// binds xml to its own namespace and no other prefix to it, and neither xmlns nor anything else to
// xmlns's namespace; it lets only the default namespace be undeclared with "". Chrome also refuses a
// namespace name it cannot read as a URI (see NAMESPACE_URI).
function isBinding(prefix, uri) {
  if (prefix === 'xmlns' || uri === XMLNS_NS || (prefix === 'xml') !== (uri === XML_NS)) return false;
  return uri === '' ? prefix === null : NAMESPACE_URI.test(uri);
}

// A name as a namespace-aware parser tells names apart: unprefixed, the name itself, which is in no
// namespace; prefixed, its local name and its prefix's namespace joined by a space, which no name can
// hold. Returns null for a prefix that is not in scope, which makes the document fail to parse, as
// xmlns does, since it is never bound.
function expandedName(name, prefixes) {
  const colon = name.indexOf(':');
  if (colon === -1) return name;
  const uri = prefixes.get(name.slice(0, colon));
  return uri === undefined ? null : `${name.slice(colon + 1)} ${uri}`;
}

// An attribute's value as a parser reads it: each literal tab, line end or carriage return a space, then
// every reference replaced by its character.
function attributeText(value) {
  return decodeXml(value.replace(/\r\n?|[\t\n]/g, ' '));
}

function isSafeAttribute(name, value) {
  if (name === 'xmlns' || name.startsWith('xmlns:')) return true;
  // xml:base would send even a fragment link elsewhere in a viewer that honours it.
  if (name === 'xml:base') return false;
  const local = localName(name);
  if (/^on/i.test(local) || DROPPED_ATTRIBUTES.test(local)) return false;
  if (URL_ATTRIBUTES.test(local)) return SAFE_URL.test(value);
  // An SVG animation can write a link or an event handler after load, so it may not target one.
  // No attribute name needs a character reference, and one could spell "href" past the check.
  if (local === 'attributeName') {
    if (value.includes('&')) return false;
    const target = localName(value.trim());
    return !/^on/i.test(target) && !URL_ATTRIBUTES.test(target) && !DROPPED_ATTRIBUTES.test(target);
  }
  // style, fill, stroke, filter, mask, clip-path and marker-* can all hold a url(); none may reach out.
  return !badCss(value);
}

// Whether CSS text, or an attribute value that may be read as CSS, can reach out: BAD_CSS as written,
// or once its character references are read (url&#40; is url( to a browser), or a backslash, written
// or referenced, which starts a CSS escape (u\72l( is url(, @\69mport is @import) that no pattern could
// see through. Neither the widget nor a panel uses one.
function badCss(value) {
  const plain = decodeXml(value);
  return BAD_CSS.test(value) || BAD_CSS.test(plain) || plain.includes('\\');
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

function escapeAttribute(text) {
  return escapeText(text).replace(/"/g, '&quot;');
}

const NAMED_ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'" };

// Turns the references sanitize lets through back into characters, in one pass so that "&amp;lt;"
// stays "&lt;". A reference to a character XML does not allow, such as &#0; or a lone surrogate, which
// sanitize refuses, becomes nothing, so text read here can always be written back into a well formed
// document.
function decodeXml(text) {
  return text.replace(/&(?:(amp|lt|gt|quot|apos)|#([0-9]+)|#x([0-9a-fA-F]+));/g, (_, name, decimal, hex) => {
    if (name) return NAMED_ENTITIES[name];
    const code = decimal ? Number(decimal) : parseInt(hex, 16);
    return isXmlChar(code) ? String.fromCodePoint(code) : '';
  });
}

function isXmlChar(code) {
  return (
    code === 0x9 || code === 0xa || code === 0xd || (code >= 0x20 && code <= 0xd7ff) ||
    (code >= 0xe000 && code <= 0xfffd) || (code >= 0x10000 && code <= 0x10ffff)
  );
}

// ---------------------------------------------------------------- composition

const SPACE = /\s*/y;
const DOCTYPE = /<!DOCTYPE[^[>]*(?:\[[^\]]*\])?\s*>/y;
const ROOT_CLOSE = /^<\/svg\s*>$/;

// Returns the sanitized markup between the root <svg ...> tag and its closing tag, or null when
// the text is not an SVG document.
export function svgInner(text) {
  return readSvg(text)?.inner ?? null;
}

// Returns { root, inner }: the root tag as readOpenTag reads it and the sanitized markup inside it,
// or null when the text is not an SVG document, or its markup nests too deep for a card (MAX_DEPTH).
function readSvg(text) {
  if (typeof text !== 'string') return null;
  const start = prologEnd(text);
  const root = start === -1 ? null : readOpenTag(text, start);
  if (!root || root.name !== 'svg' || root.selfClosing) return null;
  const end = text.trimEnd();
  const close = end.lastIndexOf('</svg');
  if (close < root.end || !ROOT_CLOSE.test(end.slice(close))) return null;
  const inner = clean(text.slice(root.end, close));
  return inner === null || inner.depth > MAX_DEPTH ? null : { root, inner: inner.markup };
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
// They move only for a viewer who allows motion, as the compact strip's and the Apple Music pane's do:
// the widget's own animation is switched off, and cpbar is switched on only inside the media query, so
// under reduced motion, playing or recently played, the bars stand still at the widget's 3px.
export const BAR_RULES =
  '#bars{position:static!important;display:flex!important;align-items:flex-end;gap:1px;' +
  'width:auto!important;height:22px!important;margin:-22px 0 0!important;overflow:hidden}' +
  '.bar{position:static!important;flex:0 0 3px;opacity:1!important;animation-name:none!important}' +
  '@media (prefers-reduced-motion: no-preference){.bar{animation-name:cpbar!important}' +
  '@keyframes cpbar{from{height:3px}to{height:22px}}}';

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
const VIGNETTE_STOPS =
  '<stop offset=".62" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".22"/>';
const RIGHT_VIGNETTE =
  `<defs><radialGradient id="vignetteRight" cx="50%" cy="48%" r="75%">${VIGNETTE_STOPS}</radialGradient></defs>` +
  '<rect x="560" width="336" height="445" rx="10" fill="url(#vignetteRight)"/>';

// What a screen reader hears for each card, by the music service it shows.
const LABELS = Object.freeze({
  spotify: 'Coding activity and now playing on Spotify',
  apple: 'Coding activity and last played on Apple Music',
});

function labelOf(service) {
  return service === 'apple' ? LABELS.apple : LABELS.spotify;
}

export function compose(panelInner, rightInner, { bg, line }, glow = false, label = LABELS.spotify) {
  return (
    '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="896" height="445" ' +
    `viewBox="0 0 896 445" role="img" aria-label="${label}">` +
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

// Returns the finished card, or null when the panel is unusable. A missing or unusable music card is
// not an error: the placeholder takes its place. Both services supply track data to the same native
// drawing; none of the upstream widget's layout or animation reaches the finished music pane.
export function buildCard(panelText, musicText, palette, { glow = false, service = 'spotify' } = {}) {
  const panel = svgInner(panelText);
  if (panel === null) return null;
  const playing = nowPlaying(svgInner(musicText), service);
  const right = playing === null ? placeholder(palette) : musicPane(playing, palette, glow, freePrefix(panel));
  return compose(panel, right, palette, glow, labelOf(service));
}

// The most bars any of the widget's themes draws.
const MAX_BARS = 100;

// With nothing playing, the widget shows a track played recently, picked at random from the last few,
// under "Recently played", and leaves its equalizer empty, though its style still places every bar.
// For such a track this puts back the bars the widget draws while a track plays, one for each bar its
// style places (75 in the default theme), so the equalizer bounces just as it does then; BAR_RULES
// lays them out as it does a playing track's, and holds them still under reduced motion. Anything else is returned as it is. inner is sanitized.
export function recentBars(inner) {
  const playing = nowPlaying(inner);
  if (playing === null || !playing.status.startsWith('Recently played')) return inner;
  const from = inner.indexOf('<style');
  const to = inner.indexOf('</style>');
  const style = from === -1 || to < from ? '' : inner.slice(from, to);
  const placed = new Set(Array.from(style.matchAll(/\.bar:nth-child\(\s*(\d+)\s*\)/g), (match) => Number(match[1])));
  const count = Math.min(placed.size, MAX_BARS);
  const at = emptyBarsEnd(inner);
  if (count === 0 || at === -1) return inner;
  return inner.slice(0, at) + '<div class="bar"></div>'.repeat(count) + inner.slice(at);
}

// Where the widget's equalizer, the element with id "bars", closes when it holds nothing but white
// space, or -1. After sanitize every "<" opens or closes a tag.
function emptyBarsEnd(inner) {
  for (let pos = inner.indexOf('<'); pos !== -1; pos = inner.indexOf('<', pos)) {
    if (inner.startsWith('</', pos)) {
      pos += 2;
      continue;
    }
    const tag = readOpenTag(inner, pos);
    if (!tag) return -1;
    pos = tag.end;
    if (localName(tag.name).toLowerCase() === 'div' && decodeXml(attributeValue(tag, 'id') ?? '') === 'bars') {
      const close = inner.indexOf('<', pos);
      const empty = !tag.selfClosing && close !== -1 && inner.startsWith('</div>', close) && !inner.slice(pos, close).trim();
      return empty ? close : -1;
    }
  }
  return -1;
}

// ---------------------------------------------------------------- the compact card

// The portrait card for phones: the profile's compact panel on top and the music card under it as
// a strip. The strip is drawn natively from what the music card carries (status, artist, song, cover
// and logo) rather than by re-laying out its foreignObject: native text and images render alike in
// every viewer, and the strip's type can be sized for a phone.
export const COMPACT = Object.freeze({ width: 360, minHeight: 400, maxHeight: 900, strip: 112 });

const GREEN = '#53b14f';
// The only images the strip draws: rasters embedded as data: URLs.
const RASTER = /^\s*data:image\/(?:png|jpe?g|gif|webp)[;,]/i;
// A plain length in user units, the way the generator writes a root's width and height.
const DIMENSION = /^[0-9]{1,4}(?:\.[0-9]{1,4})?$/;

// The strip in its own units: a square cover on the left, three lines of text and the equalizer beside it.
const PAD = 14;
const COVER = COMPACT.strip - 2 * PAD;
const TEXT_X = PAD + COVER + PAD;
const TEXT_ROOM = COMPACT.width - TEXT_X - PAD;
const LOGO = 16;

// Dark mode's glow: the shadows GLOW_RULES gives the wide card's Spotify half, as SVG filters, for what
// the relay draws natively, the strip and the wide card's Apple Music pane. A CSS blur radius is twice
// the Gaussian's standard deviation.
const NATIVE_GLOWS = Object.freeze({
  playing: Object.freeze({ deviation: 3, color: GREEN, opacity: 0.5 }),
  artist: Object.freeze({ deviation: 4, color: '#ffffff', opacity: 0.14 }),
  bars: Object.freeze({ deviation: 2, color: GREEN, opacity: 0.45 }),
});

// Returns { inner, height } for a usable compact panel: an SVG document whose root is 360 units wide
// and 400 to 900 tall, with a viewBox, when it has one, of exactly that box, and whose markup passes
// sanitize. Returns null for anything else, so the caller can fall back to the wide card.
export function readCompactPanel(text) {
  const svg = readSvg(text);
  if (svg === null) return null;
  const width = dimension(svg.root, 'width');
  const height = dimension(svg.root, 'height');
  if (width !== COMPACT.width || !(height >= COMPACT.minHeight && height <= COMPACT.maxHeight)) return null;
  const viewBox = attributeValue(svg.root, 'viewBox');
  if (viewBox !== undefined && viewBox.trim().split(/[\s,]+/).map(Number).join(' ') !== `0 0 ${width} ${height}`) {
    return null;
  }
  return { inner: svg.inner, height };
}

function attributeValue(tag, name) {
  return tag.attributes.find((attribute) => attribute.name === name)?.value;
}

function dimension(tag, name) {
  const value = attributeValue(tag, name);
  return value !== undefined && DIMENSION.test(value) ? Number(value) : NaN;
}

// The Spotify widget's fields: each comes from the first element carrying its class.
const byClass = (field) => [field, (name, classes) => classes.has(field)];
const SPOTIFY_TEXT = ['playing', 'artist', 'song'].map(byClass);
const SPOTIFY_IMAGES = ['cover', 'logo'].map(byClass);

// What a music card shows, read from its sanitized markup (svgInner's output): { status, artist, song,
// cover, logo }, the text decoded with its white space collapsed, and cover and logo each a data: raster
// or null. service is 'spotify', the default, or 'apple' (see lastPlayed). For Spotify, returns null when
// no artist is named, which is how the widget says that nothing is playing.
export function nowPlaying(inner, service = 'spotify') {
  if (service === 'apple') return lastPlayed(inner);
  const found = readFields(inner, SPOTIFY_TEXT, SPOTIFY_IMAGES);
  const artist = found === null ? '' : collapse(found.artist);
  if (!artist) return null;
  return { status: collapse(found.playing) || 'Now playing on', artist, song: collapse(found.song),
    cover: relabel(found.cover), logo: relabel(found.logo) };
}

// Reads fields from sanitized markup by rules [field, test], where test is given each element's local name,
// in lower case, and its set of classes. A text rule takes the text of the first element, not self-closing,
// that passes it, and an image rule the src of the first img that passes it and carries a data: raster.
// Returns every field, null where nothing matched, or null when the markup is not well formed.
function readFields(inner, textRules, imageRules) {
  if (typeof inner !== 'string') return null;
  const found = Object.fromEntries([...textRules, ...imageRules].map(([field]) => [field, null]));
  const feeds = []; // for each open element, the text field its text belongs to, or null
  let pos = 0;
  while (pos < inner.length) {
    const lt = inner.indexOf('<', pos);
    const field = feeds.length ? feeds[feeds.length - 1] : null;
    if (field) found[field] += inner.slice(pos, lt === -1 ? inner.length : lt);
    if (lt === -1) break;
    if (inner.startsWith('</', lt)) {
      CLOSE_TAG.lastIndex = lt;
      if (!CLOSE_TAG.exec(inner) || feeds.length === 0) return null;
      feeds.pop();
      pos = CLOSE_TAG.lastIndex;
      continue;
    }
    const tag = readOpenTag(inner, lt);
    if (!tag) return null;
    const name = localName(tag.name).toLowerCase();
    const classes = new Set(decodeXml(attributeValue(tag, 'class') ?? '').split(/\s+/));
    const passes = ([own, test]) => found[own] === null && test(name, classes);
    const src = attributeValue(tag, 'src');
    if (name === 'img' && src !== undefined && RASTER.test(src)) {
      const image = imageRules.find(passes);
      if (image) found[image[0]] = decodeXml(src).trim();
    }
    if (!tag.selfClosing) {
      const own = textRules.find(passes);
      if (own) found[own[0]] = '';
      feeds.push(own ? own[0] : field);
    }
    pos = tag.end;
  }
  return found;
}

function collapse(text) {
  return text === null ? '' : decodeXml(text).replace(/\s+/g, ' ').trim();
}

const GRAPHEMES = new Intl.Segmenter('en', { granularity: 'grapheme' });

// East Asian wide characters, emoji, and the symbols drawn as emoji (weather, hearts, stars, arrows,
// regional-indicator flags) take about a whole em.
function isWide(code) {
  return (
    (code >= 0x1100 && code <= 0x115f) || (code >= 0x2600 && code <= 0x27bf) || (code >= 0x2b00 && code <= 0x2bff) ||
    (code >= 0x2e80 && code <= 0xa4cf) || (code >= 0xac00 && code <= 0xd7a3) || (code >= 0xf900 && code <= 0xfaff) ||
    (code >= 0xfe30 && code <= 0xfe4f) || (code >= 0xff00 && code <= 0xff60) || (code >= 0xffe0 && code <= 0xffe6) ||
    (code >= 0x1f000 && code <= 0x1f2ff) || (code >= 0x1f300 && code <= 0x1faff) || (code >= 0x20000 && code <= 0x3fffd)
  );
}

// A line's estimate of each character's width in ems: wide characters a whole em, capitals cap, and
// everything else em, the fraction the prototype sized the line with.
function estimate(em, cap) {
  return (segment) => {
    const code = segment.codePointAt(0);
    if (isWide(code)) return 1;
    return code >= 0x41 && code <= 0x5a ? cap : em;
  };
}

// The status line's advance widths in thousandths of an em, bold, for each printable ASCII character
// from the space on: the mean of Segoe UI Bold and Arial Bold (Helvetica's widths), measured in Chrome.
// Its textLength is its width in these, so its letters are hardly spread or squeezed in any of them.
const STATUS_ADVANCES = [
  277, 330, 484, 574, 566, 878, 786, 266, 351, 351, 422, 646, 274, 368, 274, 360, 566, 566, 566, 566, 566, 566, 566,
  566, 566, 566, 302, 302, 646, 646, 646, 524, 964, 712, 682, 673, 730, 600, 566, 744, 744, 298, 500, 686, 561, 895,
  756, 768, 640, 768, 688, 614, 598, 722, 667, 974, 661, 637, 609, 351, 357, 351, 646, 486, 324, 547, 616, 518, 615,
  548, 358, 615, 606, 281, 281, 558, 281, 902, 608, 611, 616, 615, 394, 498, 361, 608, 549, 788, 554, 547, 490, 379,
  303, 379, 646,
];
const STATUS_ELSE = estimate(0.55, 0.72);
// Each line's widths: the status bold at 12, the artist bold at 17, the song regular at 14.
const STATUS_WIDTH = (segment) => {
  const code = segment.codePointAt(0);
  if (segment.length === 1 && code >= 0x20 && code < 0x7f) return STATUS_ADVANCES[code - 0x20] / 1000;
  return STATUS_ELSE(segment);
};
const ARTIST_WIDTH = estimate(0.6, 0.72);
const SONG_WIDTH = estimate(0.52, 0.68);

function measure(text, size, width) {
  let total = 0;
  for (const { segment } of GRAPHEMES.segment(text)) total += size * width(segment);
  return total;
}

// The text cut to fit room units at the given size, never inside a character, with an ellipsis when
// anything was cut. It stops reading as soon as the room is full, so a huge title costs no more.
function fit(text, room, size, width) {
  const ellipsis = size * width('…');
  let used = 0;
  let kept = '';
  let cut = ''; // the longest start of the text that still leaves room for the ellipsis
  for (const { segment } of GRAPHEMES.segment(text)) {
    used += size * width(segment);
    if (used > room) return `${cut.trimEnd()}…`;
    kept += segment;
    if (used <= room - ellipsis) cut = kept;
  }
  return text;
}

// The equalizer: bars whose heights come from the track, so one song always draws the same. Each
// bounces, as the widget's bars do, at a pace of its own between the widget's 350 and 500 ms, dipping
// to a fifth of its height and back up, whether the track is playing or was played recently (see
// bounce). At rest the bars stand at their full heights, 3 to tallest units. The hash's lowest bits
// repeat from bar to bar, so tallest - 2 must be odd for the heights to vary.
function equalizer(x0, x1, baseline, seed, id, tallest = 15) {
  let hash = 2166136261;
  for (const char of seed) hash = Math.imul(hash ^ char.codePointAt(0), 16777619) >>> 0;
  let out = '';
  for (let x = x0, i = 0; x + 3 <= x1; x += 5, i += 1) {
    hash = Math.imul(hash ^ i, 16777619) >>> 0;
    const height = 3 + (hash % (tallest - 2));
    const pace = 350 + ((hash >>> 8) % 151);
    out +=
      `<rect class="${id}bar" x="${x}" y="${baseline - height}" width="3" height="${height}" rx="1" fill="${GREEN}" ` +
      `fill-opacity=".55" style="animation-duration:${pace}ms"/>`;
  }
  return out;
}

// The equalizer's motion, only for a viewer who allows motion. Every bar starts from its resting
// height, so a viewer whose animation clock never starts still sees the whole equalizer. Each bar
// shrinks toward its own foot, the strip's baseline.
function bounce(id) {
  return (
    `<style>@media (prefers-reduced-motion: no-preference){@keyframes ${id}bounce{to{transform:scaleY(.2)}}` +
    `.${id}bar{transform-box:fill-box;transform-origin:50% 100%;animation:${id}bounce 425ms linear infinite alternate}}` +
    '</style>'
  );
}

// A text-shadow as a filter: the shape's alpha, blurred and tinted, under the shape itself. It works
// in the drawing's own units over the whole of it, the strip's by default, so nothing it draws is cut
// off at a bounding box.
function glowFilter(id, { deviation, color, opacity }, width = COMPACT.width, height = COMPACT.strip) {
  return (
    `<filter id="${id}" filterUnits="userSpaceOnUse" x="0" y="0" width="${width}" height="${height}" ` +
    'color-interpolation-filters="sRGB">' +
    `<feGaussianBlur in="SourceAlpha" stdDeviation="${deviation}" result="blur"/>` +
    `<feFlood flood-color="${color}" flood-opacity="${opacity}"/><feComposite in2="blur" operator="in"/>` +
    '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
  );
}

// The de-lit reference material and label turn as one physical disc. A separate screen-space light
// layer responds to that same rotating material through a luminance mask, so reflections catch the
// ridges without orbiting with the album art. Both remain still for reduced motion.
function vinyl(cover, x, y, size, palette, id) {
  const spin = `${id}vinyl-spin`;
  const record = `${id}vinyl-record`;
  const label = `${id}vinyl-label`;
  const disc = `${id}vinyl-disc`;
  const texture = `${id}vinyl-texture`;
  const glint = `${id}vinyl-glint`;
  const ridges = `${id}vinyl-ridges`;
  const response = `${id}vinyl-response`;
  const light = `${id}vinyl-light`;
  const grooves = `${id}vinyl-grooves`;
  const art = cover
    ? `<image x="23" y="23" width="54" height="54" preserveAspectRatio="xMidYMid slice" ` +
      `clip-path="url(#${label})" href="${escapeAttribute(cover)}"/>`
    : `<circle cx="50" cy="50" r="27" fill="${palette.line}"/>` +
      `<path d="M47 37v19a5 5 0 1 1-3-4.6V40l14-3v15a5 5 0 1 1-3-4.6V34z" fill="${palette.text}" fill-opacity=".55"/>`;
  return (
    `<svg x="${x}" y="${y}" width="${size}" height="${size}" viewBox="0 0 100 100" aria-hidden="true">` +
    `<defs><clipPath id="${label}"><circle cx="50" cy="50" r="27"/></clipPath>` +
    `<clipPath id="${disc}"><circle cx="50" cy="50" r="49.7"/></clipPath>` +
    `<clipPath id="${grooves}"><path clip-rule="evenodd" d="M50 .3a49.7 49.7 0 1 0 0 99.4a49.7 49.7 0 1 0 0-99.4` +
    'M50 23a27 27 0 1 0 0 54a27 27 0 1 0 0-54"/></clipPath>' +
    `<radialGradient id="${light}"><stop stop-color="#fff" stop-opacity=".55"/>` +
    '<stop offset=".5" stop-color="#dce2eb" stop-opacity=".3"/><stop offset="1" stop-color="#dce2eb" stop-opacity="0"/></radialGradient>' +
    `<filter id="${response}" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">` +
    '<feComponentTransfer><feFuncR type="linear" slope="2.4"/><feFuncG type="linear" slope="2.4"/>' +
    '<feFuncB type="linear" slope="2.4"/></feComponentTransfer></filter>' +
    `<mask id="${ridges}" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse" x="0" y="0" width="100" height="100" ` +
    `style="mask-type:luminance"><g filter="url(#${response})">` +
    `<g class="${record}"><use href="#${texture}"/></g></g></mask></defs>` +
    `<style>@media (prefers-reduced-motion: no-preference){@keyframes ${spin}{to{transform:rotate(360deg)}}` +
    `@keyframes ${glint}{0%,100%{transform:rotate(-2deg);opacity:.94}50%{transform:rotate(2deg);opacity:1}}` +
    `.${record},.${glint}{transform-box:view-box;transform-origin:50% 50%}` +
    `.${record}{animation:${spin} 12s linear infinite}.${glint}{animation:${glint} 4s ease-in-out infinite}}</style>` +
    `<g clip-path="url(#${disc})"><g class="${record}" data-vinyl-body="true">` +
    '<circle cx="50" cy="50" r="49.7" fill="#0b0b0c"/>' +
    // Align the 1254px texture's inner opening (626,599) with the label/pivot, not its eccentric outer bounds.
    // Uniform scaling keeps its opaque material beyond the outer circular clip through every rotation.
    `<image id="${texture}" data-vinyl-texture="true" x="-6.1603" y="-3.7380" width="112.5" height="112.5" ` +
    `preserveAspectRatio="none" href="${VINYL_TEXTURE}"/>${art}</g>` +
    `<g mask="url(#${ridges})" clip-path="url(#${grooves})" pointer-events="none"><g class="${glint}">` +
    `<ellipse cx="74" cy="24" rx="16" ry="40" transform="rotate(45 74 24)" fill="url(#${light})"/>` +
    `<ellipse cx="26" cy="76" rx="16" ry="40" transform="rotate(45 26 76)" fill="url(#${light})"/></g></g></g>` +
    '<circle cx="50" cy="50" r="27" fill="none" stroke="#000" stroke-opacity=".4" stroke-width=".3"/>' +
    '</svg>'
  );
}

// The strip's markup in its own 360 by 112 units. With nothing playing it is the wide card's
// placeholder, moved from the middle of that card's 320 by 445 pane to the middle of the strip.
function strip(playing, palette, glow, id) {
  if (playing === null) return `<g transform="translate(20 -165)">${placeholder(palette)}</g>`;
  const { text, muted } = palette;
  const filter = (name) => (glow ? ` filter="url(#${id}glow-${name})"` : '');
  const glows = glow ? Object.entries(NATIVE_GLOWS).map(([name, spec]) => glowFilter(`${id}glow-${name}`, spec)).join('') : '';
  let out =
    `<defs><clipPath id="${id}text"><rect width="${COMPACT.width - PAD}" height="${COMPACT.strip}"/></clipPath>${glows}</defs>`;
  out += vinyl(playing.cover, PAD, PAD, COVER, palette, id);
  // The text column ends at the padding, even where a line runs wider than its estimate.
  out += `<g clip-path="url(#${id}text)">`;
  // The status is set to its measured width, so the logo can sit right after it in any font.
  const status = fit(playing.status, TEXT_ROOM - (playing.logo ? LOGO + 5 : 0), 12, STATUS_WIDTH);
  const statusWidth = measure(status, 12, STATUS_WIDTH).toFixed(1);
  out +=
    `<text x="${TEXT_X}" y="${PAD + 12}" font-family="${SANS}" font-size="12" font-weight="700" fill="${GREEN}" ` +
    `textLength="${statusWidth}" lengthAdjust="spacing"${filter('playing')}>${escapeText(status)}</text>`;
  if (playing.logo) {
    out +=
      `<image x="${(TEXT_X + Number(statusWidth) + 5).toFixed(1)}" y="${PAD}" width="${LOGO}" height="${LOGO}" ` +
      `preserveAspectRatio="xMidYMid meet" href="${escapeAttribute(playing.logo)}"/>`;
  }
  out +=
    `<text x="${TEXT_X}" y="${PAD + 39}" font-family="${SANS}" font-size="17" font-weight="700" fill="${text}"` +
    `${filter('artist')}>${escapeText(fit(playing.artist, TEXT_ROOM, 17, ARTIST_WIDTH))}</text>`;
  if (playing.song) {
    out +=
      `<text x="${TEXT_X}" y="${PAD + 59}" font-family="${SANS}" font-size="14" fill="${muted}">` +
      `${escapeText(fit(playing.song, TEXT_ROOM, 14, SONG_WIDTH))}</text>`;
  }
  out += '</g>';
  const bars = equalizer(TEXT_X, COMPACT.width - PAD, PAD + COVER, playing.artist + playing.song, id);
  return out + bounce(id) + (glow ? `<g${filter('bars')}>${bars}</g>` : bars);
}

// A prefix for the relay's own ids that begins none of the panel's ids, so the two can never collide:
// relay-, or relay1-, relay2- and so on when the panel already uses it. Ids are compared decoded,
// since id="&#114;elay-card" names the same element as id="relay-card".
function freePrefix(markup) {
  const taken = new Set();
  for (const [, quoted] of markup.matchAll(/\s(?:[A-Za-z_][\w.-]*:)?id=("[^"]*"|'[^']*')/g)) {
    const match = /^relay([0-9]*)-/.exec(decodeXml(quoted.slice(1, -1)));
    if (match) taken.add(match[1]);
  }
  let n = 0;
  while (taken.has(n === 0 ? '' : String(n))) n += 1;
  return n === 0 ? 'relay-' : `relay${n}-`;
}

// Returns the compact card for a panel read by readCompactPanel, or null when there is none. As with
// buildCard, a missing or unusable music card is not an error: the strip says nothing is playing, and
// service names the music card in the same way. In dark mode the strip glows as the wide card's music
// half does, and it gets its own vignette, as that half does, so the two parts of the card darken alike
// where they meet.
export function buildCompactCard(panel, musicText, palette, { glow = false, service = 'spotify' } = {}) {
  if (panel === null) return null;
  const { width, strip: stripHeight } = COMPACT;
  const top = panel.height;
  const height = top + stripHeight;
  const id = freePrefix(panel.inner);
  const { bg, line } = palette;
  const vignette = `<radialGradient id="${id}vignette" cx="50%" cy="48%" r="75%">${VIGNETTE_STOPS}</radialGradient>`;
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${width}" height="${height}" ` +
    `viewBox="0 0 ${width} ${height}" role="img" aria-label="${labelOf(service)}">` +
    `<defs><clipPath id="${id}card"><rect width="${width}" height="${height}" rx="10"/></clipPath>` +
    `${glow ? vignette : ''}</defs>` +
    `<rect width="${width}" height="${height}" rx="10" fill="${bg}"/>` +
    `<svg x="0" y="0" width="${width}" height="${top}" viewBox="0 0 ${width} ${top}">${panel.inner}</svg>` +
    `<rect y="${top}" width="${width}" height="${stripHeight}" fill="url(#grid)" clip-path="url(#${id}card)"/>` +
    `<line x1="${PAD}" y1="${top}" x2="${width - PAD}" y2="${top}" stroke="${line}"/>` +
    `<svg x="0" y="${top}" width="${width}" height="${stripHeight}" viewBox="0 0 ${width} ${stripHeight}">` +
    `${strip(nowPlaying(svgInner(musicText), service), palette, glow, id)}</svg>` +
    (glow
      ? `<rect y="${top}" width="${width}" height="${stripHeight}" fill="url(#${id}vignette)" clip-path="url(#${id}card)"/>`
      : '') +
    '</svg>'
  );
}

// ---------------------------------------------------------------- Apple Music

// rayriffy/apple-music-github-profile answers with a card of its own design, under the GNU Affero General
// Public License rather than coderprint's, so the relay passes none of its markup or style on. It reads
// three facts from the card, the song, the artist and the cover, and draws them itself: in the compact
// card's strip, as it draws Spotify's, and in the wide card's right pane (musicPane). The service
// asks Apple Music only for the track played last, never for what is playing, so the status says so. No
// logo is drawn: Apple Music's is Apple's trademark, so the service is named in plain text.
const APPLE_STATUS = 'Last played on Apple Music';
// The song and the artist are the card's h1.song-title and h2.song-artist, and the cover its
// img.cover-image. The service answers a failure, an unknown uid or a lapsed Apple Music session, with
// an error card carrying a bug icon and a "Failure!" heading, sent as a success.
const APPLE_TEXT = [
  ['song', (name, classes) => name === 'h1' && classes.has('song-title')],
  ['artist', (name, classes) => name === 'h2' && classes.has('song-artist')],
  ['heading', (name) => name === 'h1'],
  ['bug', (name, classes) => classes.has('bug-icon')],
];
const APPLE_IMAGES = [['cover', (name, classes) => classes.has('cover-image')]];

// What Apple Music's card names, as nowPlaying returns it, or null when the card is unusable: not well
// formed, the error card, or without both a song and an artist.
function lastPlayed(inner) {
  const found = readFields(inner, APPLE_TEXT, APPLE_IMAGES);
  if (found === null || found.bug !== null || collapse(found.heading).startsWith('Failure')) return null;
  const song = collapse(found.song);
  const artist = collapse(found.artist);
  if (!song || !artist) return null;
  return { status: APPLE_STATUS, artist, song, cover: relabel(found.cover), logo: null };
}

const BASE64_RASTER = /^data:image\/(?:png|jpe?g|gif|webp);base64,/i;

// A cover given as a base64 data: URL, decoded and encoded again under the type its bytes show, or null
// when they are not a PNG, JPEG, GIF or WebP image. The service labels every cover image/webp, though
// the ones it passes on from Apple are JPEG, and a viewer may refuse an image its label misnames.
function relabel(url) {
  const head = typeof url === 'string' ? BASE64_RASTER.exec(url) : null;
  if (!head) return null;
  const data = url.slice(head[0].length).replace(/[\t\n\f\r ]+/g, '');
  if (data.length % 4 !== 0 || !/^[A-Za-z0-9+/]*={0,2}$/.test(data)) return null;
  const bytes = Buffer.from(data, 'base64');
  const type = imageType(bytes);
  return type === null ? null : `data:${type};base64,${bytes.toString('base64')}`;
}

// The image type that bytes begin with, by its signature, or null.
function imageType(bytes) {
  const starts = (...signature) => signature.every((byte, i) => bytes[i] === byte);
  if (starts(0xff, 0xd8, 0xff)) return 'image/jpeg';
  if (starts(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a)) return 'image/png';
  if (starts(0x47, 0x49, 0x46, 0x38)) return 'image/gif';
  if (starts(0x52, 0x49, 0x46, 0x46) && bytes.length >= 12 && bytes.toString('latin1', 8, 12) === 'WEBP') return 'image/webp';
  return null;
}

// The same record and typography for either provider, preserving what the provider actually knows:
// Spotify's now/recently playing status or Apple Music's last-played status.
const PANE = Object.freeze({ width: 320, height: 445, pad: 10, cover: 300, coverY: 131 });

function musicPane(playing, palette, glow, id) {
  const { text, muted } = palette;
  const { width, height, pad, cover, coverY } = PANE;
  const middle = width / 2;
  const room = width - 2 * pad;
  const filter = (name) => (glow ? ` filter="url(#${id}glow-${name})"` : '');
  const glows = glow
    ? Object.entries(NATIVE_GLOWS).map(([name, spec]) => glowFilter(`${id}glow-${name}`, spec, width, height)).join('')
    : '';
  // One centred line, cut to fit the room.
  const centred = (y, size, bold, fill, words, widths, effect = '') =>
    `<text x="${middle}" y="${y}" text-anchor="middle" font-family="${SANS}" font-size="${size}"` +
    `${bold ? ' font-weight="700"' : ''} fill="${fill}"${effect}>${escapeText(fit(words, room, size, widths))}</text>`;
  let out = `<defs>${glows}</defs>`;
  if (playing.logo) {
    const status = fit(playing.status, room - 31, 16, STATUS_WIDTH);
    const statusWidth = measure(status, 16, STATUS_WIDTH);
    const x = (width - statusWidth - 31) / 2;
    out += `<text x="${x.toFixed(1)}" y="32" font-family="${SANS}" font-size="16" font-weight="700" fill="${GREEN}" ` +
      `textLength="${statusWidth.toFixed(1)}" lengthAdjust="spacing"${filter('playing')}>${escapeText(status)}</text>` +
      `<image x="${(x + statusWidth + 7).toFixed(1)}" y="11" width="24" height="24" ` +
      `preserveAspectRatio="xMidYMid meet" href="${escapeAttribute(playing.logo)}"/>`;
  } else {
    out += centred(32, 16, true, GREEN, playing.status, STATUS_WIDTH, filter('playing'));
  }
  out += centred(76, 20, true, text, playing.artist, ARTIST_WIDTH, filter('artist'));
  out += centred(101, 16, false, muted, playing.song, SONG_WIDTH);
  const bars = equalizer(pad, width - pad, coverY - 2, playing.artist + playing.song, id, 21);
  out += bounce(id) + (glow ? `<g${filter('bars')}>${bars}</g>` : bars);
  out += vinyl(playing.cover, pad, coverY, cover, palette, id);
  return out;
}
