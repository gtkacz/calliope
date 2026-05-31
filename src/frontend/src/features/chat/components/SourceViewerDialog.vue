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

// Highlight the passage inside the rendered document by wrapping the matching
// run of each involved text node in a <mark>. Matching is done on a
// whitespace-normalized projection of the DOM text with a per-character map back
// to the originating text node, so highlights survive element boundaries.
function highlightPassage(container: HTMLElement, passage: string): boolean {
  const needle = passagePlainText(passage).toLowerCase();
  if (needle.length === 0) return false;

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
  if (start === -1) return false;
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

  for (const range of ranges) {
    let segment = range.node;
    if (range.start > 0) segment = segment.splitText(range.start);
    if (range.end - range.start < segment.data.length) {
      segment.splitText(range.end - range.start);
    }
    const mark = document.createElement("mark");
    mark.className = "source-doc__hit";
    segment.parentNode?.replaceChild(mark, segment);
    mark.appendChild(segment);
  }
  return true;
}

watch(
  () => renderedContent.value,
  async () => {
    matched.value = null;
    await nextTick();
    const container = bodyRef.value;
    const passage = viewer.content?.passage;
    if (container === null || !passage) return;
    matched.value = highlightPassage(container, passage);
    if (matched.value) {
      await nextTick();
      container
        .querySelector(".source-doc__hit")
        ?.scrollIntoView({ block: "center", behavior: "smooth" });
    }
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

/* The cited passage — a warm gilt highlight evoking a manuscript rubrication. */
.source-doc__body :deep(.source-doc__hit) {
  background: var(--calliope-bronze-veil);
  color: var(--calliope-paper);
  box-shadow:
    inset 0 -0.55em 0 var(--calliope-bronze-veil),
    0 0 0 1px var(--calliope-bronze-glow);
  border-radius: var(--calliope-radius-xs);
  padding: 0.04em 0.06em;
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
