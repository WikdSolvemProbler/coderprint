// Reads a pull request description and says whether it answers what CONTRIBUTING.md asks of every
// contribution: Who, What, When, Where and Why, and, when the contributor ticks the box saying the pull request
// questions a decision or claim in coderprint, How and Evidence as well. The workflow
// .github/workflows/contribution-check.yml runs it from the base branch with the description in PR_BODY; it
// never runs the contributor's code. It prints only fixed text and never echoes the description, so nothing a
// contributor writes can become a workflow command.
import { appendFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

export const WS = ['Who', 'What', 'When', 'Where', 'Why'];
export const CHALLENGE = ['How', 'Evidence'];
const NAMES = new Set([...WS, ...CHALLENGE].map((name) => name.toLowerCase()));

export const CHECKBOX_TEXT = 'This pull request questions a decision or claim in coderprint';
// The box as people write it: a bullet or a number, inside a quote or not, and spaces inside the brackets.
const CHECKBOX = /^\s{0,3}(?:>\s*)*(?:[-*+]|\d+[.)])\s+\[\s*([xX]?)\s*\]\s+this pull request questions a decision or claim in coderprint\b/i;

// Answers that hold a place without answering anything.
const PLACEHOLDERS = new Set(['n/a', 'na', 'none', 'tbd', 'todo', '...', '…', '?', '-', '_no response_', 'no response']);

// An http or https link to a named host, or a Digital Object Identifier (DOI) such as 10.1145/1453101.1453146.
const LINK = /\bhttps?:\/\/[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}(?![a-z0-9-])/i;
const DOI = /\b10\.\d{4,9}\/[^\s<>"]+/;

const HEADING = /^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$/;
const FENCE = /^ {0,3}(`{3,}|~{3,})/;

// Windows and old Mac line endings become \n, and HyperText Markup Language (HTML) comments go, including one
// left open, which GitHub also hides to the end of the description.
export function normalize(body) {
  const text = typeof body === 'string' ? body : '';
  return text.replace(/\r\n?/g, '\n').replace(/<!--[\s\S]*?(-->|$)/g, '');
}

// Splits the description into the sections named in NAMES, keyed by lowercase name, each a list of lines, and
// reports the challenge box: null when absent, otherwise whether it is ticked. A section runs from its heading
// to the next heading of the same or a higher level, or to the next heading that names a section. Headings
// inside fenced code do not count, and the checkbox line belongs to no section.
export function parseSections(body) {
  const sections = new Map();
  let checkbox = null;
  let current = null;
  let fence = null;
  for (const line of normalize(body).split('\n')) {
    const opens = FENCE.exec(line);
    if (fence) {
      if (opens && opens[1][0] === fence[0] && opens[1].length >= fence.length && line.trim() === opens[1]) fence = null;
      current?.lines.push(line);
      continue;
    }
    if (opens) {
      fence = opens[1];
      current?.lines.push(line);
      continue;
    }
    const box = CHECKBOX.exec(line);
    if (box) {
      checkbox = checkbox === true || box[1] !== '';
      continue;
    }
    const heading = HEADING.exec(line);
    if (heading) {
      const level = heading[1].length;
      const text = (heading[2] ?? '').replace(/[ \t]+#+$/, '').replace(/^#+$/, '').trim();
      // "### Who", "### Who:" or "### Who?", and an answer written on the heading line after a colon or question
      // mark ("### Who: profile owners") counts as the section's first line.
      const named = /^([A-Za-z]+)[ \t]*([:?]?)[ \t]*(.*)$/.exec(text);
      const name = named && NAMES.has(named[1].toLowerCase()) && (named[3] === '' || named[2] !== '')
        ? named[1].toLowerCase() : '';
      if (name) {
        if (!sections.has(name)) sections.set(name, []);
        current = { level, lines: sections.get(name) };
        if (named[3]) current.lines.push(named[3]);
        continue;
      }
      if (current && level <= current.level) current = null;
      continue;
    }
    current?.lines.push(line);
  }
  return { sections, checkbox };
}

// True when a line says something: not blank, not bare Markdown punctuation, HyperText Markup Language (HTML)
// tags or entities, an empty task box, or a placeholder, however it is marked up (**N/A**, `TBD`).
function says(line) {
  const text = line.replace(/<[^>]*>/g, ' ').replace(/&(?:[a-z]+|#\d+|#x[0-9a-f]+);/gi, ' ').trim();
  if (/^[-*_>#|=+`~\s]*$/.test(text)) return false;
  const bare = text.replace(/^([-*+>]|\d+[.)])\s+/, '').replace(/^\[\s*[xX]?\s*\]/, '')
    .trim().replace(/^[*_`~]+|[*_`~]+$/g, '').trim().toLowerCase();
  if (!bare) return false;
  return !PLACEHOLDERS.has(bare) && !PLACEHOLDERS.has(bare.replace(/\.$/, ''));
}

const answered = (lines) => (lines ?? []).some(says);

const ASK = {
  Who: 'Who: say who is affected or who benefits.',
  What: 'What: say what changes, or what is wrong.',
  When: 'When: say when it happens, or when the change should apply.',
  Where: 'Where: name the files, parts of the card or settings involved.',
  Why: 'Why: give the reason and the problem it solves.',
};

// The whole check. Returns ok, and one friendly sentence for each thing still missing.
export function checkBody(body) {
  const { sections, checkbox } = parseSections(body);
  const missing = [];
  for (const name of WS) {
    if (!answered(sections.get(name.toLowerCase()))) missing.push(ASK[name]);
  }
  if (checkbox === null) {
    missing.push(`The checkbox "${CHECKBOX_TEXT}" is gone: put it back, ticked if this pull request questions a decision or claim, empty if it does not.`);
  }
  if (checkbox === true) {
    if (!answered(sections.get('how'))) {
      missing.push('How: you ticked the box, so say how you suggest the logic be improved, or how this pull request improves it.');
    }
    const evidence = (sections.get('evidence') ?? []).filter(says).join('\n');
    if (!LINK.test(evidence) && !DOI.test(evidence)) {
      missing.push('Evidence: you ticked the box, so cite at least one source with an http or https link or a Digital Object Identifier (DOI) such as 10.1145/1453101.1453146, and say in a sentence or two what it shows and how it applies.');
    }
  }
  return { ok: missing.length === 0, missing };
}

export function report({ ok, missing }) {
  if (ok) return 'The description answers Who, What, When, Where and Why, and How and Evidence where they are required. Thank you.';
  return [
    'Thank you for the pull request. Before review, the description needs a little more:',
    '',
    ...missing.map((item) => `  * ${item}`),
    '',
    'Edit the pull request description (not the code) and this check runs again by itself.',
    'The headings are ### Who, ### What, ### When, ### Where, ### Why, ### How and ### Evidence; see CONTRIBUTING.md.',
  ].join('\n');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const result = checkBody(process.env.PR_BODY ?? null);
  const text = report(result);
  console.log(text);
  if (process.env.GITHUB_STEP_SUMMARY) {
    try {
      appendFileSync(process.env.GITHUB_STEP_SUMMARY, `## Contribution check\n\n${text}\n`);
    } catch {
      // The summary is a courtesy; the exit code is the verdict.
    }
  }
  if (!result.ok) {
    console.log(`::error title=Contribution check::The pull request description is missing ${result.missing.length} required answer${result.missing.length === 1 ? '' : 's'}. The log lists them.`);
    process.exitCode = 1;
  }
}
