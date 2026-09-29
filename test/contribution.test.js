// The contribution check reads a pull request description and fails it unless it answers Who, What, When,
// Where and Why, and, when the challenge box is ticked, How and Evidence. Every rule is tried both ways, on the
// untouched template, on filled ones and on the ways people really write, and the script is also run as the
// workflow runs it, to prove the exit code and that it never echoes the description.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { CHECKBOX_TEXT, checkBody, parseSections } from '../.github/scripts/contribution-check.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SCRIPT = join(ROOT, '.github/scripts/contribution-check.mjs');

const TEMPLATE = `### Who
<!-- Who is affected, or who benefits? -->

### What
<!-- What changes, or what is wrong? -->

### When
<!-- When does it happen, or when should it apply? -->

### Where
<!-- Which files, parts of the card or settings? -->

### Why
<!-- The reason, and the problem it solves. -->

- [ ] ${CHECKBOX_TEXT}

### How
<!-- Required when the box is checked: how you suggest the logic be improved, or how this pull request improves it. -->

### Evidence
<!-- Required when the box is checked: at least one source, with a link or a Digital Object Identifier (DOI). -->
`;

const ANSWERS = {
  Who: 'Anyone whose panel uses the sepia theme.',
  What: 'The legend text is too faint to read.',
  When: 'Every day the sepia theme is drawn.',
  Where: 'The legend in coderprint.py.',
  Why: 'Text below the contrast minimum is hard to read.',
};

// Fills the template: each answer goes under its heading, the comment left in place as a contributor leaves it.
function fill(answers, { ticked = false, template = TEMPLATE } = {}) {
  let body = template;
  for (const [name, answer] of Object.entries(answers)) {
    body = body.replace(new RegExp(`(### ${name}\\n<!--[^\\n]*-->\\n)`), `$1${answer}\n`);
  }
  return ticked ? body.replace('- [ ] ', '- [x] ') : body;
}

const FILLED = fill(ANSWERS);
const DOI_EVIDENCE = 'Bettenburg and others, "What Makes a Good Bug Report?", 2008, doi:10.1145/1453101.1453146. Developers rate steps to reproduce most helpful.';
const LINK_EVIDENCE = 'Web Content Accessibility Guidelines (WCAG) 2.2, contrast minimum, https://www.w3.org/TR/WCAG22/#contrast-minimum, sets 4.5 to 1 for body text.';
const HOW = 'Raise the legend colour to the ink colour, as this pull request does.';

const missingNames = (body) => checkBody(body).missing.map((line) => line.split(':')[0]);

test('the untouched template fails, naming all five Ws and nothing else', () => {
  const result = checkBody(TEMPLATE);
  assert.equal(result.ok, false);
  assert.deepEqual(missingNames(TEMPLATE), ['Who', 'What', 'When', 'Where', 'Why']);
});

test('a filled template passes', () => {
  assert.deepEqual(checkBody(FILLED), { ok: true, missing: [] });
});

test('each of the five Ws is required on its own', () => {
  for (const name of Object.keys(ANSWERS)) {
    const answers = { ...ANSWERS };
    delete answers[name];
    assert.deepEqual(missingNames(fill(answers)), [name], `leaving out ${name}`);
  }
});

test('a null, undefined or empty description fails', () => {
  for (const body of [null, undefined, '', '   \n\n']) {
    const result = checkBody(body);
    assert.equal(result.ok, false);
    assert.deepEqual(result.missing.slice(0, 5).map((line) => line.split(':')[0]), ['Who', 'What', 'When', 'Where', 'Why']);
  }
});

test('an unticked box asks for neither How nor Evidence', () => {
  assert.equal(checkBody(FILLED).ok, true);
  assert.equal(checkBody(FILLED.replace('### How\n', '### How\nNothing to add here.\n')).ok, true);
});

test('a ticked box without How or Evidence fails on both', () => {
  assert.deepEqual(missingNames(fill(ANSWERS, { ticked: true })), ['How', 'Evidence']);
});

test('a ticked box with How but no link or DOI fails on Evidence', () => {
  const body = fill({ ...ANSWERS, How: HOW, Evidence: 'I measured it and it looked better to me.' }, { ticked: true });
  assert.deepEqual(missingNames(body), ['Evidence']);
});

test('a ticked box with evidence but no How fails on How', () => {
  const body = fill({ ...ANSWERS, Evidence: DOI_EVIDENCE }, { ticked: true });
  assert.deepEqual(missingNames(body), ['How']);
});

test('a ticked box with How and a DOI passes', () => {
  assert.equal(checkBody(fill({ ...ANSWERS, How: HOW, Evidence: DOI_EVIDENCE }, { ticked: true })).ok, true);
  assert.equal(checkBody(fill({ ...ANSWERS, How: HOW, Evidence: 'See 10.1109/TSE.2022.3224053 on template length.' }, { ticked: true })).ok, true);
});

test('a ticked box with How and an https link passes, and a capital X ticks it too', () => {
  const body = fill({ ...ANSWERS, How: HOW, Evidence: LINK_EVIDENCE }, { ticked: true });
  assert.equal(checkBody(body).ok, true);
  assert.equal(checkBody(body.replace('- [x] ', '- [X] ')).ok, true);
  assert.equal(parseSections(body.replace('- [x] ', '* [X] ')).checkbox, true);
});

test('Evidence needs a real link or DOI, not something shaped like one', () => {
  for (const evidence of ['http://localhost/report', 'https://', 'see 10.12/x', 'DOI pending', 'www.example.com without a scheme']) {
    const body = fill({ ...ANSWERS, How: HOW, Evidence: evidence }, { ticked: true });
    assert.deepEqual(missingNames(body), ['Evidence'], evidence);
  }
  const plain = fill({ ...ANSWERS, How: HOW, Evidence: 'http://example.org/study' }, { ticked: true });
  assert.equal(checkBody(plain).ok, true);
});

test('a link or DOI that sits only inside a comment is not evidence', () => {
  const body = fill({ ...ANSWERS, How: HOW, Evidence: '<!-- https://example.org 10.1145/1453101.1453146 -->' }, { ticked: true });
  assert.deepEqual(missingNames(body), ['Evidence']);
});

test('a link under another heading does not stand in for Evidence', () => {
  const body = fill({ ...ANSWERS, Why: `${ANSWERS.Why} https://example.org/why`, How: HOW }, { ticked: true });
  assert.deepEqual(missingNames(body), ['Evidence']);
});

test('headings in any case, at any level, with trailing spaces, a colon or closing hashes, still count', () => {
  const variants = [
    (body) => body.replace(/^### (\w+)$/gm, (_, name) => `### ${name.toUpperCase()}`),
    (body) => body.replace(/^### (\w+)$/gm, (_, name) => `### ${name.toLowerCase()}   `),
    (body) => body.replace(/^### (\w+)$/gm, '## $1:'),
    (body) => body.replace(/^### (\w+)$/gm, '#### $1 ####'),
    (body) => body.replace(/^### (\w+)$/gm, '   ### $1\t'),
  ];
  for (const variant of variants) {
    const ticked = variant(fill({ ...ANSWERS, How: HOW, Evidence: DOI_EVIDENCE }, { ticked: true }));
    assert.deepEqual(checkBody(ticked), { ok: true, missing: [] }, ticked);
    assert.equal(checkBody(variant(TEMPLATE)).ok, false);
  }
});

test('Windows and old Mac line endings are read like any other', () => {
  const ticked = fill({ ...ANSWERS, How: HOW, Evidence: LINK_EVIDENCE }, { ticked: true });
  for (const ending of ['\r\n', '\r']) {
    assert.deepEqual(checkBody(ticked.replace(/\n/g, ending)), { ok: true, missing: [] });
    assert.deepEqual(missingNames(TEMPLATE.replace(/\n/g, ending)), ['Who', 'What', 'When', 'Where', 'Why']);
    assert.deepEqual(missingNames(fill(ANSWERS, { ticked: true }).replace(/\n/g, ending)), ['How', 'Evidence']);
  }
});

test('placeholder answers count as empty', () => {
  for (const placeholder of ['N/A', 'n/a.', 'None', 'TBD', 'todo', '...', '?', '-', '_No response_', '- n/a', '---', '> ', '|  |']) {
    assert.deepEqual(missingNames(fill({ ...ANSWERS, Who: placeholder })), ['Who'], placeholder);
  }
  assert.equal(checkBody(fill({ ...ANSWERS, Who: 'None of the current users; new users on Windows.' })).ok, true);
});

test('placeholders dressed in markup, empty task boxes, tags and entities count as empty', () => {
  for (const placeholder of ['**N/A**', '*n/a*', '`TBD`', '_none_', '~~todo~~', '- [ ]', '- [x]', '&nbsp;', '<br>', '<p></p>', '**`N/A`**']) {
    assert.deepEqual(missingNames(fill({ ...ANSWERS, Who: placeholder })), ['Who'], placeholder);
  }
  assert.equal(checkBody(fill({ ...ANSWERS, Who: '**Profile owners** on Windows.' })).ok, true);
});

test('an answer written on the heading line after a colon or question mark counts', () => {
  const inline = FILLED.replace(/### Who\n<!--[^\n]*-->\n[^\n]*\n/, '### Who: anyone whose panel uses the sepia theme.\n');
  assert.equal(checkBody(inline).ok, true, inline);
  const asked = FILLED.replace('### Who\n', '### Who?\n');
  assert.equal(checkBody(asked).ok, true);
  const empty = FILLED.replace(/### Who\n<!--[^\n]*-->\n[^\n]*\n/, '### Who:\n');
  assert.deepEqual(missingNames(empty), ['Who']);
  // A longer heading that merely starts with a section name is some other heading.
  const other = FILLED.replace('### Who\n', '### Who is affected\n');
  assert.deepEqual(missingNames(other), ['Who']);
});

test('the box counts however it is written: spaces inside, numbered, or quoted', () => {
  const answered = fill({ ...ANSWERS, How: HOW, Evidence: DOI_EVIDENCE });
  for (const box of [`- [ x ] ${CHECKBOX_TEXT}`, `1. [x] ${CHECKBOX_TEXT}`, `> - [X] ${CHECKBOX_TEXT}`, `* [x]  ${CHECKBOX_TEXT}`]) {
    const body = answered.replace(`- [ ] ${CHECKBOX_TEXT}`, box);
    assert.equal(parseSections(body).checkbox, true, box);
    assert.equal(checkBody(body).ok, true, box);
  }
  for (const box of [`- [  ] ${CHECKBOX_TEXT}`, `1. [ ] ${CHECKBOX_TEXT}`, `> - [ ] ${CHECKBOX_TEXT}`]) {
    assert.equal(parseSections(FILLED.replace(`- [ ] ${CHECKBOX_TEXT}`, box)).checkbox, false, box);
  }
});

test('a section holding only comments is empty, and an unclosed comment hides the rest', () => {
  assert.deepEqual(missingNames(fill({ ...ANSWERS, Who: '<!-- still thinking -->\n<!--\nmore\n-->' })), ['Who']);
  // Build answered sections without template guidance, so no later comment closes the unclosed one.
  const cut = [
    '### Who', ANSWERS.Who, '', '### What', ANSWERS.What, '',
    '<!-- an unclosed comment', '### When', ANSWERS.When, '',
    '### Where', ANSWERS.Where, '', '### Why', ANSWERS.Why, '',
    `- [ ] ${CHECKBOX_TEXT}`,
  ].join('\n');
  assert.deepEqual(missingNames(cut), ['When', 'Where', 'Why', 'The checkbox "This pull request questions a decision or claim in coderprint" is gone']);
});

test('headings inside fenced code do not count, and fenced text still answers the section it sits in', () => {
  const fenced = `### Why\nThe log says so:\n\`\`\`\n### Who\n### What\n### When\n### Where\n\`\`\`\n\n- [ ] ${CHECKBOX_TEXT}\n`;
  assert.deepEqual(missingNames(fenced), ['Who', 'What', 'When', 'Where']);
  const tilde = FILLED.replace('### Where\n', '~~~\n### Where\n~~~\n');
  assert.deepEqual(missingNames(tilde), ['Where']);
});

test('text under an unrelated heading does not answer the section above it', () => {
  const body = FILLED.replace(`${ANSWERS.Why}\n`, '\n### Screenshots\nA picture of the legend.\n');
  assert.deepEqual(missingNames(body), ['Why']);
  const deeper = FILLED.replace(`${ANSWERS.Why}\n`, '#### Detail\nThe legend is faint.\n');
  assert.equal(checkBody(deeper).ok, true);
});

test('the checkbox line does not answer Why, and removing it fails the check', () => {
  assert.deepEqual(missingNames(fill({ ...ANSWERS, Why: '' })), ['Why']);
  const gone = FILLED.replace(`- [ ] ${CHECKBOX_TEXT}\n`, '');
  assert.equal(checkBody(gone).ok, false);
  assert.match(checkBody(gone).missing.join(' '), /checkbox/);
  assert.equal(parseSections(FILLED).checkbox, false);
  assert.equal(parseSections(gone).checkbox, null);
});

// Whatever template the repository ships must fail untouched and pass once the five Ws are written under it; a
// line of guidance left outside a comment would otherwise answer a W for every contributor.
test('the repository pull request template fails untouched and passes filled', (t) => {
  const found = ['.github/pull_request_template.md', '.github/PULL_REQUEST_TEMPLATE.md', 'pull_request_template.md',
    'PULL_REQUEST_TEMPLATE.md', 'docs/pull_request_template.md', 'docs/PULL_REQUEST_TEMPLATE.md']
    .map((path) => join(ROOT, path)).find((path) => existsSync(path));
  if (!found) {
    t.skip('the repository has no pull request template');
    return;
  }
  const template = readFileSync(found, 'utf8');
  assert.deepEqual(missingNames(template), ['Who', 'What', 'When', 'Where', 'Why'], 'the template itself answers a W, so an untouched template would pass');
  assert.equal(parseSections(template).checkbox, false, 'the template must carry the challenge checkbox, unticked');
  const filled = template
    .replace(/^(### Who[ \t]*)$/m, `$1\n${ANSWERS.Who}`).replace(/^(### What[ \t]*)$/m, `$1\n${ANSWERS.What}`)
    .replace(/^(### When[ \t]*)$/m, `$1\n${ANSWERS.When}`).replace(/^(### Where[ \t]*)$/m, `$1\n${ANSWERS.Where}`)
    .replace(/^(### Why[ \t]*)$/m, `$1\n${ANSWERS.Why}`);
  assert.deepEqual(checkBody(filled), { ok: true, missing: [] });
});

function run(body) {
  const env = { ...process.env, GITHUB_STEP_SUMMARY: '' };
  if (body === undefined) delete env.PR_BODY;
  else env.PR_BODY = body;
  return spawnSync(process.execPath, [SCRIPT], { env, encoding: 'utf8', timeout: 30_000 });
}

test('run as the workflow runs it, the script exits 0 on a good description and 1 on a bad one', () => {
  const good = run(FILLED);
  assert.equal(good.status, 0, good.stderr);
  assert.doesNotMatch(good.stdout, /::error/);
  const bad = run(TEMPLATE);
  assert.equal(bad.status, 1);
  assert.match(bad.stdout, /Who: say who is affected/);
  assert.match(bad.stdout, /::error title=Contribution check::/);
  assert.equal(run(undefined).status, 1);
  assert.equal(run('').status, 1);
});

test('the script never echoes the description, so a description cannot issue workflow commands', () => {
  const marker = 'MARKER-7f3a9c';
  const hostile = `::add-mask::${marker}\n::set-output name=x::${marker}\n### Who\n${marker}\n### Evidence\n${marker}\n`;
  for (const body of [hostile, fill({ ...ANSWERS, Who: marker }), fill({ ...ANSWERS, How: marker }, { ticked: true })]) {
    const result = run(body);
    assert.doesNotMatch(result.stdout + result.stderr, new RegExp(marker));
  }
});
