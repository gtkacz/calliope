<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { renderMarkdown } from "@/shared/markdown";
import { useChatStore } from "../stores/chatStore";

const chat = useChatStore();

type PanelView = "edit" | "preview";
const view = ref<PanelView>("edit");

// Local draft keeps the textarea in sync without creating feedback loops when
// the store canvas is updated externally (e.g. from a write turn response).
const draft = ref(chat.canvas);

// Debounce timer handle for autosave
let saveTimer: ReturnType<typeof setTimeout> | null = null;

function onUserInput(event: Event) {
  const target = event.target as HTMLTextAreaElement;
  draft.value = target.value;
  chat.canvas = target.value;

  if (saveTimer !== null) {
    clearTimeout(saveTimer);
  }
  // Capture the session being edited so a debounce that fires after the user
  // switches sessions can't write this draft into a different session's canvas.
  const editedSessionId = chat.activeSessionId;
  saveTimer = setTimeout(() => {
    saveTimer = null;
    if (chat.activeSessionId !== editedSessionId) {
      return;
    }
    void chat.saveCanvas();
  }, 700);
}

// Refresh draft when the store canvas changes externally (e.g. after a write
// turn), but only when the value actually differs to avoid caret jumps.
watch(
  () => chat.canvas,
  (next) => {
    if (next !== draft.value) {
      draft.value = next;
    }
  },
);

// Switching sessions abandons any pending autosave from the previous session.
watch(
  () => chat.activeSessionId,
  () => {
    if (saveTimer !== null) {
      clearTimeout(saveTimer);
      saveTimer = null;
    }
  },
);

// A debounce outliving the component would fire saveCanvas against whatever
// session is active at unmount; cancel it.
onBeforeUnmount(() => {
  if (saveTimer !== null) {
    clearTimeout(saveTimer);
  }
});

const renderedCanvas = computed<string>(() =>
  draft.value.length > 0 ? renderMarkdown(draft.value) : "",
);
</script>

<template>
  <div class="canvas-panel">
    <header class="canvas-panel__header">
      <span class="calliope-eyebrow canvas-panel__eyebrow">Canvas</span>
      <div
        class="canvas-panel__segmented"
        role="tablist"
        aria-label="Canvas view"
      >
        <button
          type="button"
          class="canvas-panel__segment"
          :class="{ 'is-active': view === 'edit' }"
          role="tab"
          :aria-selected="view === 'edit'"
          @click="view = 'edit'"
        >
          Edit
        </button>
        <button
          type="button"
          class="canvas-panel__segment"
          :class="{ 'is-active': view === 'preview' }"
          role="tab"
          :aria-selected="view === 'preview'"
          @click="view = 'preview'"
        >
          Preview
        </button>
      </div>
    </header>

    <div class="canvas-panel__body">
      <div v-if="view === 'edit'" class="canvas-panel__edit-wrap">
        <textarea
          class="canvas-panel__textarea calliope-mono"
          :value="draft"
          placeholder="Your canvas is empty. Start a write turn to generate content, or type directly here."
          spellcheck="true"
          aria-label="Canvas editor"
          @input="onUserInput"
        />
      </div>

      <div v-else class="canvas-panel__preview">
        <div
          v-if="renderedCanvas.length > 0"
          class="canvas-panel__markdown markdown-body"
          v-html="renderedCanvas"
        />
        <div v-else class="canvas-panel__empty">
          <p class="calliope-eyebrow canvas-panel__empty-label">Empty</p>
          <p class="canvas-panel__empty-body">
            Switch to Edit view to start writing, or send a write turn to
            generate content.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.canvas-panel {
  display: grid;
  grid-template-rows: auto 1fr;
  min-height: 0;
  background: var(--calliope-ink-soft);
}

.canvas-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--calliope-space-sm) var(--calliope-space-xl);
  border-bottom: 1px solid var(--calliope-border-strong);
  background: var(--calliope-ink-soft);
}

.canvas-panel__eyebrow {
  color: var(--calliope-paper-dim);
}

.canvas-panel__segmented {
  display: inline-flex;
  padding: 0.2rem;
  background: var(--calliope-ink);
  border-radius: var(--calliope-radius-pill);
  border: 1px solid var(--calliope-border-strong);
}

.canvas-panel__segment {
  padding: 0.28rem 0.85rem;
  background: transparent;
  border: none;
  border-radius: var(--calliope-radius-pill);
  cursor: pointer;
  font-family: var(--calliope-font-body);
  font-size: 0.75rem;
  font-weight: 460;
  letter-spacing: 0.005em;
  color: var(--calliope-paper-dim);
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-fast) var(--calliope-ease-out);
}

.canvas-panel__segment:hover {
  color: var(--calliope-paper);
}

.canvas-panel__segment:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--calliope-bronze-veil);
}

.canvas-panel__segment.is-active {
  background: var(--calliope-bronze);
  color: var(--calliope-ink);
  font-weight: 560;
  box-shadow: 0 0 10px 1px var(--calliope-bronze-glow);
}

.canvas-panel__segment.is-active:hover {
  color: var(--calliope-ink);
}

.canvas-panel__body {
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.canvas-panel__edit-wrap {
  flex: 1;
  display: flex;
  min-height: 0;
}

.canvas-panel__textarea {
  flex: 1;
  width: 100%;
  min-height: 0;
  padding: var(--calliope-space-xl);
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  font-family: var(--calliope-font-mono);
  font-size: 0.88rem;
  line-height: 1.7;
  color: var(--calliope-paper);
  /* Slight inset to match the manuscript reading feel */
  caret-color: var(--calliope-bronze);
}

.canvas-panel__textarea::placeholder {
  color: var(--calliope-paper-dim);
}

.canvas-panel__preview {
  flex: 1;
  overflow-y: auto;
  padding: var(--calliope-space-xl);
}

.canvas-panel__markdown {
  color: var(--calliope-paper);
  font-family: var(--calliope-font-body);
  font-size: 0.965rem;
  line-height: 1.7;
}

/* Markdown prose styles mirror AssistantTurn's .markdown-body rules */
.canvas-panel__markdown :deep(> :first-child) {
  margin-top: 0;
}

.canvas-panel__markdown :deep(> :last-child) {
  margin-bottom: 0;
}

.canvas-panel__markdown :deep(p) {
  margin: 0 0 0.85em;
}

.canvas-panel__markdown :deep(h1),
.canvas-panel__markdown :deep(h2),
.canvas-panel__markdown :deep(h3),
.canvas-panel__markdown :deep(h4),
.canvas-panel__markdown :deep(h5),
.canvas-panel__markdown :deep(h6) {
  font-family: var(--calliope-font-display);
  font-weight: 460;
  color: var(--calliope-paper);
  letter-spacing: -0.012em;
  line-height: 1.2;
  margin: 1.35em 0 0.55em;
}

.canvas-panel__markdown :deep(h1) { font-size: 1.4rem; }
.canvas-panel__markdown :deep(h2) { font-size: 1.22rem; }
.canvas-panel__markdown :deep(h3) { font-size: 1.08rem; }

.canvas-panel__markdown :deep(h4),
.canvas-panel__markdown :deep(h5),
.canvas-panel__markdown :deep(h6) {
  font-size: 0.98rem;
}

.canvas-panel__markdown :deep(strong) {
  font-weight: 600;
  color: var(--calliope-paper);
}

.canvas-panel__markdown :deep(em) {
  font-style: italic;
}

.canvas-panel__markdown :deep(a) {
  color: var(--calliope-bronze);
  text-decoration: none;
  border-bottom: 1px solid var(--calliope-bronze-glow);
}

.canvas-panel__markdown :deep(ul),
.canvas-panel__markdown :deep(ol) {
  margin: 0 0 0.85em;
  padding-left: 1.4em;
}

.canvas-panel__markdown :deep(li) {
  margin-bottom: 0.3em;
}

.canvas-panel__markdown :deep(li::marker) {
  color: var(--calliope-paper-dim);
}

.canvas-panel__markdown :deep(blockquote) {
  margin: 0 0 0.85em;
  padding: 0.15em 0 0.15em 1em;
  border-left: 2px solid var(--calliope-bronze);
  color: var(--calliope-paper-muted);
  font-style: italic;
}

.canvas-panel__markdown :deep(code) {
  font-family: var(--calliope-font-mono);
  font-size: 0.86em;
  background: var(--calliope-ink-raised);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-xs);
  padding: 0.08em 0.36em;
}

.canvas-panel__markdown :deep(pre) {
  margin: 0 0 0.85em;
  padding: 0.85rem 1rem;
  background: var(--calliope-ink);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-sm);
  overflow-x: auto;
}

.canvas-panel__markdown :deep(pre code) {
  font-size: 0.82rem;
  line-height: 1.6;
  background: none;
  border: none;
  border-radius: 0;
  padding: 0;
}

.canvas-panel__markdown :deep(hr) {
  margin: 1.2em 0;
  border: none;
  border-top: 1px solid var(--calliope-border);
}

.canvas-panel__markdown :deep(table) {
  margin: 0 0 0.85em;
  border-collapse: collapse;
  font-size: 0.9em;
}

.canvas-panel__markdown :deep(th),
.canvas-panel__markdown :deep(td) {
  padding: 0.4em 0.7em;
  border: 1px solid var(--calliope-border);
  text-align: left;
}

.canvas-panel__markdown :deep(th) {
  font-weight: 600;
  color: var(--calliope-paper);
  background: var(--calliope-overlay-hover);
}

.canvas-panel__empty {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  margin: auto;
  max-width: 32rem;
  text-align: center;
  padding: var(--calliope-space-2xl);
}

.canvas-panel__empty-label {
  color: var(--calliope-paper-dim);
}

.canvas-panel__empty-body {
  margin: 0;
  color: var(--calliope-paper-muted);
  font-size: 0.9rem;
  line-height: 1.6;
}
</style>
