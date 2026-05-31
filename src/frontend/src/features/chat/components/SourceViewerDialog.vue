<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";

import { renderMarkdown } from "@/shared/markdown";
import { useSourceViewerStore } from "../stores/sourceViewerStore";

const viewer = useSourceViewerStore();

const bodyRef = ref<HTMLElement | null>(null);
const matched = ref<boolean | null>(null);

const renderedContent = computed<string>(() =>
  viewer.content ? renderMarkdown(viewer.content.content) : "",
);

function filename(path: string): string {
  const parts = path.split("/");
  return parts[parts.length - 1] ?? path;
}

// Collapse every run of whitespace to a single space so a passage that the
// renderer reflowed across block boundaries still matches the document body.
function normalize(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

// Render the passage through the same markdown pipeline and take its plain text,
// so syntax the renderer strips (#, *, list markers) can't defeat the match.
function passagePlainText(passage: string): string {
  const host = document.createElement("div");
  host.innerHTML = renderMarkdown(passage);
  return normalize(host.textContent ?? "");
}

interface CharSource {
  node: Text;
  offset: number;
}

function rangeTop(node: Text, start: number, end: number): number {
  const range = document.createRange();
  range.setStart(node, start);
  range.setEnd(node, end);
  return range.getBoundingClientRect().top;
}

// Break a [from, to) run on one text node into per-visual-line spans by watching
// for jumps in each character's top offset. Reads only — no mutation — so the
// browser measures layout once and serves every rect from cache. Per-line spans
// let the sweep run one line at a time instead of all lines at once.
function splitRangeByLine(
  node: Text,
  from: number,
  to: number,
): { start: number; end: number }[] {
  const spans: { start: number; end: number }[] = [];
  let segmentStart = from;
  let previousTop = rangeTop(node, from, from + 1);
  for (let i = from + 1; i < to; i += 1) {
    const top = rangeTop(node, i, i + 1);
    if (Math.abs(top - previousTop) > 1) {
      spans.push({ start: segmentStart, end: i });
      segmentStart = i;
      previousTop = top;
    }
  }
  spans.push({ start: segmentStart, end: to });
  return spans;
}

// Highlight the passage inside the rendered document by wrapping the matching
// run of each involved text node in a <mark>. Matching is done on a
// whitespace-normalized projection of the DOM text with a per-character map back
// to the originating text node, so highlights survive element boundaries.
// Returns the created marks (in document order) so the caller can sweep them on.
function highlightPassage(container: HTMLElement, passage: string): HTMLElement[] {
  const needle = passagePlainText(passage).toLowerCase();
  if (needle.length === 0) return [];

  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  let normalized = "";
  const charSources: CharSource[] = [];
  let lastWasSpace = false;
  let current = walker.nextNode() as Text | null;
  while (current !== null) {
    const text = current.data;
    for (let i = 0; i < text.length; i += 1) {
      const isSpace = /\s/.test(text[i]);
      if (isSpace) {
        if (lastWasSpace || normalized.length === 0) continue;
        normalized += " ";
        charSources.push({ node: current, offset: i });
        lastWasSpace = true;
      } else {
        normalized += text[i];
        charSources.push({ node: current, offset: i });
        lastWasSpace = false;
      }
    }
    current = walker.nextNode() as Text | null;
  }

  const start = normalized.toLowerCase().indexOf(needle);
  if (start === -1) return [];
  const end = start + needle.length;

  // Group matched normalized characters by their source node into contiguous
  // raw [start, end) ranges, then wrap each range. Collect before mutating so
  // splitText calls on one node never disturb another.
  const ranges: { node: Text; start: number; end: number }[] = [];
  for (let i = start; i < end; i += 1) {
    const { node, offset } = charSources[i];
    const tail = ranges[ranges.length - 1];
    if (tail !== undefined && tail.node === node && offset === tail.end) {
      tail.end = offset + 1;
    } else {
      ranges.push({ node, start: offset, end: offset + 1 });
    }
  }

  // Expand each per-node run into per-visual-line spans, trimming whitespace off
  // every line's edges so the sweep runs line-by-line and blank gaps / wrapped
  // line-end spaces never get a highlight box of their own. All measuring happens
  // here, before any DOM mutation, so layout is read in one cached pass.
  const spans: { node: Text; start: number; end: number }[] = [];
  for (const range of ranges) {
    const data = range.node.data;
    for (const line of splitRangeByLine(range.node, range.start, range.end)) {
      let from = line.start;
      let to = line.end;
      while (from < to && /\s/.test(data[from])) from += 1;
      while (to > from && /\s/.test(data[to - 1])) to -= 1;
      if (from < to) spans.push({ node: range.node, start: from, end: to });
    }
  }

  // Wrap each line span in its own <mark>. Cut each node's spans high-offset first
  // so an earlier splitText never shifts an offset still to be cut; markByIndex
  // preserves document (top-to-bottom) order for the staggered sweep.
  const markByIndex: (HTMLElement | undefined)[] = new Array(spans.length);
  const indicesByNode = new Map<Text, number[]>();
  spans.forEach((span, index) => {
    const list = indicesByNode.get(span.node);
    if (list === undefined) indicesByNode.set(span.node, [index]);
    else list.push(index);
  });
  for (const [node, indices] of indicesByNode) {
    const descending = [...indices].sort((a, b) => spans[b].start - spans[a].start);
    const head = node;
    for (const index of descending) {
      const span = spans[index];
      let fragment = head;
      if (span.start > 0) fragment = fragment.splitText(span.start);
      if (span.end - span.start < fragment.data.length) {
        fragment.splitText(span.end - span.start);
      }
      const mark = document.createElement("mark");
      mark.className = "source-doc__hit";
      fragment.parentNode?.replaceChild(mark, fragment);
      mark.appendChild(fragment);
      markByIndex[index] = mark;
    }
  }

  const marks = markByIndex.filter(
    (mark): mark is HTMLElement => mark !== undefined,
  );
  assignSweepTiming(marks);
  return marks;
}

// Inverse of an easeInOutQuart curve: given a fraction of the passage's content,
// return the fraction of real time at which a slow-fast-slow stroke reaches it.
// The macro easing has to live here — in how each line's start/duration is spaced
// across the timeline — because the per-line fill itself is linear. Distributing
// delays along this inverse is what makes the whole sweep ease in, rush the
// middle, and settle at the end (a per-line timing-function only eases each tiny
// segment, which reads as constant speed overall).
function inverseEaseTime(contentFraction: number): number {
  const c = Math.min(1, Math.max(0, contentFraction));
  return c < 0.5
    ? Math.pow(c / 8, 1 / 4)
    : 1 - Math.pow(2 * (1 - c), 1 / 4) / 2;
}

// Lay the marks (one per visual line) out along the eased timeline: each line is
// painted left-to-right, in order, but the cadence down the passage follows the
// slow-fast-slow curve. Timing rides on CSS custom properties read by the paint
// animation, whose own timing-function stays linear.
function assignSweepTiming(marks: HTMLElement[]): void {
  const lengths = marks.map((mark) => (mark.textContent ?? "").length);
  const totalChars = lengths.reduce((sum, length) => sum + length, 0) || 1;
  const totalMs = Math.min(1500, Math.max(420, totalChars * 9));
  let elapsedChars = 0;
  marks.forEach((mark, index) => {
    const startTime = inverseEaseTime(elapsedChars / totalChars);
    const endTime = inverseEaseTime((elapsedChars + lengths[index]) / totalChars);
    const delay = Math.round(totalMs * startTime);
    const duration = Math.max(1, Math.round(totalMs * (endTime - startTime)));
    mark.style.setProperty("--paint-duration", `${duration}ms`);
    mark.style.setProperty("--paint-delay", `${delay}ms`);
    elapsedChars += lengths[index];
  });
}

const PAINTING_CLASS = "source-doc__body--painting";

watch(
  () => renderedContent.value,
  async () => {
    matched.value = null;
    // Drop any prior sweep state so reopening replays the stroke from scratch.
    bodyRef.value?.classList.remove(PAINTING_CLASS);
    await nextTick();
    const container = bodyRef.value;
    const passage = viewer.content?.passage;
    if (container === null || !passage) return;

    const marks = highlightPassage(container, passage);
    matched.value = marks.length > 0;
    if (marks.length === 0) return;

    await nextTick();
    marks[0].scrollIntoView({ block: "center", behavior: "smooth" });

    // Draw the highlight only once scrolling settles, so the sweep reads as a
    // deliberate stroke rather than racing the scroll. scrollend is the precise
    // signal; the timeout covers browsers without it and the no-scroll case.
    const scroller = container.closest(".source-doc__scroll");
    let started = false;
    const begin = () => {
      if (started) return;
      started = true;
      container.classList.add(PAINTING_CLASS);
    };
    scroller?.addEventListener("scrollend", begin, { once: true });
    window.setTimeout(begin, 520);
  },
);

function close() {
  viewer.hide();
}
</script>

<template>
  <v-dialog
    :model-value="viewer.open"
    max-width="780"
    scrollable
    @update:model-value="(value) => { if (!value) close(); }"
  >
    <div class="source-doc">
      <header class="source-doc__head">
        <div class="source-doc__meta">
          <span class="calliope-eyebrow source-doc__eyebrow">Source</span>
          <h2 class="source-doc__title calliope-serif">
            {{ viewer.content?.title || (viewer.source ? filename(viewer.source.path) : "Document") }}
          </h2>
          <span
            v-if="viewer.source"
            class="source-doc__path calliope-mono"
          >{{ viewer.source.path }}</span>
          <span
            v-if="viewer.source?.heading"
            class="source-doc__heading calliope-mono"
          >§ {{ viewer.source.heading }}</span>
        </div>
        <button
          type="button"
          class="source-doc__close"
          aria-label="Close source"
          @click="close"
        >
          <v-icon icon="$mdi-close" size="18" />
        </button>
      </header>

      <div class="source-doc__scroll">
        <div v-if="viewer.loading" class="source-doc__state calliope-mono">
          Loading source…
        </div>
        <div v-else-if="viewer.errorMessage" class="source-doc__state source-doc__state--error">
          {{ viewer.errorMessage }}
        </div>
        <template v-else>
          <p
            v-if="matched === false && viewer.source"
            class="source-doc__note calliope-mono"
          >
            Cited passage shown below — exact location couldn’t be pinpointed in the rendered text.
          </p>
          <!-- Document body is indexed markdown; renderMarkdown sanitizes before v-html. -->
          <div ref="bodyRef" class="source-doc__body markdown-body" v-html="renderedContent" />
        </template>
      </div>
    </div>
  </v-dialog>
</template>

<style scoped>
.source-doc {
  display: flex;
  flex-direction: column;
  max-height: 82vh;
  background: var(--calliope-ink-soft);
  border: 1px solid var(--calliope-border-strong);
  border-radius: var(--calliope-radius-lg);
  box-shadow: var(--calliope-shadow-lift);
  overflow: hidden;
}

.source-doc__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--calliope-space-md);
  padding: 1.25rem 1.4rem 1rem;
  border-bottom: 1px solid var(--calliope-border-strong);
  background: var(--calliope-ink-raised);
  position: relative;
}

/* Gilt hairline echoing the manuscript section-rule motif */
.source-doc__head::after {
  content: "";
  position: absolute;
  bottom: -1px;
  left: 1.4rem;
  right: 1.4rem;
  height: 1px;
  background: linear-gradient(
    to right,
    var(--calliope-bronze) 0%,
    var(--calliope-rule) 60%,
    transparent 100%
  );
  opacity: 0.4;
}

.source-doc__meta {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.source-doc__eyebrow {
  color: var(--calliope-bronze);
  letter-spacing: 0.24em;
}

.source-doc__title {
  margin: 0.1rem 0 0;
  font-size: 1.3rem;
  font-weight: 440;
  letter-spacing: -0.012em;
  color: var(--calliope-paper);
}

.source-doc__path {
  font-size: 0.72rem;
  color: var(--calliope-paper-muted);
  letter-spacing: 0.02em;
  word-break: break-all;
}

.source-doc__heading {
  font-size: 0.72rem;
  color: var(--calliope-bronze);
  letter-spacing: 0.01em;
}

.source-doc__close {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-sm);
  color: var(--calliope-paper-muted);
  cursor: pointer;
  transition:
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    background-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.source-doc__close:hover {
  color: var(--calliope-paper);
  border-color: var(--calliope-border-strong);
  background: var(--calliope-overlay-hover);
}

.source-doc__scroll {
  overflow-y: auto;
  padding: 1.4rem 1.5rem 1.6rem;
}

.source-doc__state {
  color: var(--calliope-paper-dim);
  font-size: 0.8rem;
  letter-spacing: 0.04em;
  padding: 1.5rem 0;
  text-align: center;
}

.source-doc__state--error {
  color: var(--calliope-warm-error);
}

.source-doc__note {
  margin: 0 0 1rem;
  padding: 0.5rem 0.7rem;
  font-size: 0.7rem;
  letter-spacing: 0.02em;
  color: var(--calliope-paper-dim);
  border-left: 2px solid var(--calliope-border-strong);
  background: var(--calliope-overlay-hover);
  border-radius: 0 var(--calliope-radius-sm) var(--calliope-radius-sm) 0;
}

.source-doc__body {
  color: var(--calliope-paper);
  font-family: var(--calliope-font-chat);
  font-size: 0.95rem;
  line-height: 1.75;
}

/* The cited passage — a gilt marker stroke. It renders un-painted (zero-width
   background) and is swept on left-to-right once the scroll settles (see the
   PAINTING_CLASS toggle), so it reads like a highlighter being drawn. The
   two-tone band sits low like real ink pressed harder at the base. */
.source-doc__body :deep(.source-doc__hit) {
  /* Translucent gilt ink, derived from the bronze token so it stays on-palette —
     the dark page reads through it like a real highlighter rather than a solid
     fill. Two-tone: lighter at the top, a touch denser at the base. */
  --source-hit-soft: color-mix(in srgb, yellow 30%, transparent);
  --source-hit-strong: color-mix(in srgb, yellow 30%, transparent);
  color: var(--calliope-paper);
  /* <mark> ships a solid-yellow UA background; clear it so only the gilt gradient
     shows and the un-swept state is genuinely transparent (not opaque yellow). */
  background-color: transparent;
  border-radius: var(--calliope-radius-xs);
  /* Vertical padding only — horizontal padding would shift line wrapping and
     invalidate the per-line measurement the sweep depends on. */
  padding: 0.08em 0;
  background-image: linear-gradient(
    180deg,
    transparent 8%,
    var(--source-hit-soft) 8%,
    var(--source-hit-soft) 52%,
    var(--source-hit-strong) 52%,
    var(--source-hit-strong) 90%,
    transparent 90%
  );
  background-repeat: no-repeat;
  background-position: left center;
  background-size: 0% 100%;
}

/* Per-line fill is linear; the slow-fast-slow character of the whole sweep comes
   from the eased delay/duration spacing assigned in assignSweepTiming(). */
.source-doc__body--painting :deep(.source-doc__hit) {
  animation: source-doc-paint var(--paint-duration, 480ms) linear
    var(--paint-delay, 0ms) both;
}

@keyframes source-doc-paint {
  from {
    background-size: 0% 100%;
  }
  to {
    background-size: 100% 100%;
  }
}

/* Honour reduced-motion: show the highlight fully drawn, no sweep. */
@media (prefers-reduced-motion: reduce) {
  .source-doc__body :deep(.source-doc__hit) {
    background-size: 100% 100%;
  }
  .source-doc__body--painting :deep(.source-doc__hit) {
    animation: none;
  }
}

/* Compact editorial typography for the rendered document body. Kept local to the
   viewer (no drop-cap, wider measure) rather than coupling to the chat turn. */
.source-doc__body :deep(> :first-child) {
  margin-top: 0;
}

.source-doc__body :deep(p) {
  margin: 0 0 0.85em;
}

.source-doc__body :deep(h1),
.source-doc__body :deep(h2),
.source-doc__body :deep(h3),
.source-doc__body :deep(h4),
.source-doc__body :deep(h5),
.source-doc__body :deep(h6) {
  font-family: var(--calliope-font-display);
  font-weight: 460;
  color: var(--calliope-paper);
  letter-spacing: -0.012em;
  line-height: 1.25;
  margin: 1.3em 0 0.5em;
}

.source-doc__body :deep(h1) {
  font-size: 1.45rem;
}

.source-doc__body :deep(h2) {
  font-size: 1.22rem;
}

.source-doc__body :deep(h3) {
  font-size: 1.06rem;
}

.source-doc__body :deep(strong) {
  font-weight: 600;
  color: var(--calliope-paper);
}

.source-doc__body :deep(em) {
  font-style: italic;
}

.source-doc__body :deep(ul),
.source-doc__body :deep(ol) {
  margin: 0 0 0.85em;
  padding-left: 1.4em;
}

.source-doc__body :deep(li) {
  margin-bottom: 0.3em;
}

.source-doc__body :deep(li::marker) {
  color: var(--calliope-paper-dim);
}

.source-doc__body :deep(blockquote) {
  margin: 0 0 0.85em;
  padding: 0.15em 0 0.15em 1em;
  border-left: 2px solid var(--calliope-bronze);
  color: var(--calliope-paper-muted);
  font-style: italic;
}

.source-doc__body :deep(code) {
  font-family: var(--calliope-font-mono);
  font-size: 0.86em;
  background: var(--calliope-ink-raised);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-xs);
  padding: 0.08em 0.36em;
}

.source-doc__body :deep(pre) {
  margin: 0 0 0.85em;
  padding: 0.85rem 1rem;
  background: var(--calliope-ink);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-sm);
  overflow-x: auto;
}

.source-doc__body :deep(pre code) {
  background: none;
  border: none;
  padding: 0;
}

.source-doc__body :deep(hr) {
  margin: 1.2em 0;
  border: none;
  border-top: 1px solid var(--calliope-border);
}

.source-doc__body :deep(a) {
  color: var(--calliope-bronze);
  text-decoration: none;
  border-bottom: 1px solid var(--calliope-bronze-glow);
}
</style>
