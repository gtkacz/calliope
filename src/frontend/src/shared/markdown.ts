import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";

// One parser instance, configured once and reused for every render.
const md = new MarkdownIt({
  html: false, // raw HTML in the source is escaped rather than emitted (defense in depth)
  linkify: false, // off: cited file paths (foo.md, foo.co) would otherwise be mangled into bogus links
  breaks: true, // a single newline becomes <br>, matching how chat output is authored
  typographer: true, // smart quotes and dashes suit the editorial type treatment
});

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
