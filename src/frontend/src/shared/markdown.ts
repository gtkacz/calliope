import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";
import type StateCore from "markdown-it/lib/rules_core/state_core.mjs";
import type Token from "markdown-it/lib/token.mjs";

// One parser instance, configured once and reused for every render.
const md = new MarkdownIt({
  html: false, // raw HTML in the source is escaped rather than emitted (defense in depth)
  linkify: false, // off: cited file paths (foo.md, foo.co) would otherwise be mangled into bogus links
  breaks: true, // a single newline becomes <br>, matching how chat output is authored
  typographer: true, // smart quotes and dashes suit the editorial type treatment
});

// A source citation is a parenthetical naming one or more document paths separated
// by ';', e.g. "(Characters/Section Z/Gawel.md; Setting Description.md)". The model
// emits these inline; we lift them into styled tags rather than leaving raw prose.
const CITATION_GROUP = /\(([^()]+)\)/g;
const FILE_LIKE = /\.[A-Za-z0-9]{1,8}$/;

function citationSegments(inner: string): string[] | null {
  const segments = inner
    .split(";")
    .map((segment) => segment.trim())
    .filter((segment) => segment.length > 0);
  // Only treat the group as a citation when every segment names a file; this leaves
  // ordinary parentheticals such as "(see chapter 3)" as plain text.
  if (segments.length === 0 || !segments.every((s) => FILE_LIKE.test(s))) {
    return null;
  }
  return segments;
}

function citationMarkup(segments: string[]): string {
  const items = segments
    .map((path) => {
      const fullPath = md.utils.escapeHtml(path);
      const base = md.utils.escapeHtml(path.slice(path.lastIndexOf("/") + 1));
      // data-path lets the chat view resolve the chip back to a retrieved source
      // and open the full document; title surfaces the full path on hover.
      return `<span class="md-citation__item" data-path="${fullPath}" title="${fullPath}">${base}</span>`;
    })
    .join("");
  return `<span class="md-citation" role="note" aria-label="Cited sources">${items}</span>`;
}

// Rewrite citation runs inside already-parsed inline content. Working on `text`
// tokens only means citations sitting inside code spans/blocks are left untouched.
function splitTextToken(token: Token, state: StateCore): Token[] {
  const text = token.content;
  CITATION_GROUP.lastIndex = 0;
  const out: Token[] = [];
  let cursor = 0;
  let match: RegExpExecArray | null;
  while ((match = CITATION_GROUP.exec(text)) !== null) {
    const segments = citationSegments(match[1]);
    if (segments === null) continue;
    if (match.index > cursor) {
      const lead = new state.Token("text", "", 0);
      lead.content = text.slice(cursor, match.index);
      out.push(lead);
    }
    const chip = new state.Token("html_inline", "", 0);
    chip.content = citationMarkup(segments);
    out.push(chip);
    cursor = match.index + match[0].length;
  }
  if (out.length === 0) return [token];
  if (cursor < text.length) {
    const tail = new state.Token("text", "", 0);
    tail.content = text.slice(cursor);
    out.push(tail);
  }
  return out;
}

function citationRule(state: StateCore): void {
  for (const block of state.tokens) {
    if (block.type !== "inline" || block.children === null) continue;
    const rebuilt: Token[] = [];
    for (const child of block.children) {
      if (child.type === "text") {
        rebuilt.push(...splitTextToken(child, state));
      } else {
        rebuilt.push(child);
      }
    }
    block.children = rebuilt;
  }
}

md.core.ruler.push("calliope_citation", citationRule);

// An attribution line such as "*Source: Setting Description.md (Section "…")*".
// The model emits these as a standalone (usually italic) paragraph; we lift the
// whole line into a styled, clickable footnote rather than leaving it as prose.
const SOURCE_PREFIX = /^\s*(Sources?)\s*:\s*(.*)$/s;
const TRAILING_PAREN = /\s*(\([^()]*\))\s*$/;

function collectInnerText(tokens: Token[], from: number, to: number): string | null {
  let text = "";
  for (let index = from; index < to; index += 1) {
    const token = tokens[index];
    if (token.type !== "text" && token.type !== "softbreak") return null;
    text += token.type === "softbreak" ? " " : token.content;
  }
  return text;
}

function sourceNoteMarkup(label: string, body: string): string {
  const locationMatch = TRAILING_PAREN.exec(body);
  const location = locationMatch !== null ? locationMatch[1] : "";
  const reference = (location !== "" ? body.slice(0, locationMatch!.index) : body).trim();
  const safeLabel = md.utils.escapeHtml(label);
  const safeReference = md.utils.escapeHtml(reference);
  const dataPath = md.utils.escapeHtml(reference);
  const locationMarkup =
    location !== ""
      ? `<span class="md-source__loc">${md.utils.escapeHtml(location)}</span>`
      : "";
  return (
    `<span class="md-source" role="note" data-path="${dataPath}">` +
    `<span class="md-source__label">${safeLabel}</span>` +
    `<span class="md-source__ref">${safeReference}</span>` +
    `${locationMarkup}</span>`
  );
}

// Replace a child-token run [from, to) (inclusive of an em wrapper, or just the
// lone text token) with a single html_inline source-note token.
function buildSourceNoteToken(state: StateCore, label: string, body: string): Token {
  const token = new state.Token("html_inline", "", 0);
  token.content = sourceNoteMarkup(label, body);
  return token;
}

function sourceNoteRule(state: StateCore): void {
  for (const block of state.tokens) {
    if (block.type !== "inline" || block.children === null) continue;
    const children = block.children;

    // Case A: the whole line is wrapped in emphasis — em_open … text … em_close.
    if (
      children.length >= 3 &&
      children[0].type === "em_open" &&
      children[children.length - 1].type === "em_close"
    ) {
      const inner = collectInnerText(children, 1, children.length - 1);
      const match = inner !== null ? SOURCE_PREFIX.exec(inner) : null;
      if (match !== null) {
        block.children = [buildSourceNoteToken(state, match[1], match[2])];
        continue;
      }
    }

    // Case B: a bare attribution paragraph with no emphasis.
    if (children.length === 1 && children[0].type === "text") {
      const match = SOURCE_PREFIX.exec(children[0].content);
      if (match !== null) {
        block.children = [buildSourceNoteToken(state, match[1], match[2])];
      }
    }
  }
}

md.core.ruler.push("calliope_source_note", sourceNoteRule);

// External links should open in a new tab; rel closes the reverse-tabnabbing vector.
DOMPurify.addHook("afterSanitizeAttributes", (node) => {
  if (node.tagName === "A" && node.hasAttribute("href")) {
    node.setAttribute("target", "_blank");
    node.setAttribute("rel", "noopener noreferrer");
  }
});

export function renderMarkdown(source: string): string {
  return DOMPurify.sanitize(md.render(source));
}
