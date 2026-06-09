<script setup lang="ts">
import { computed } from 'vue'

import { renderMarkdown } from '@/shared/markdown'

import type { SourceReference } from '../types'
import { useSourceViewerStore } from '../stores/sourceViewerStore'
import CopyMessageButton from './CopyMessageButton.vue'
import SourceChip from './SourceChip.vue'

const props = defineProps<{
  role: string
  content: string
  sources?: SourceReference[]
  truncated?: boolean
  contextOverflow?: boolean
}>()

const viewer = useSourceViewerStore()

const renderedContent = computed<string>(() => renderMarkdown(props.content))

function displayRole(role: string): string {
  if (role === 'assistant') return 'Calliope'
  if (role === 'search') return 'Search'
  return role.charAt(0).toUpperCase() + role.slice(1)
}

function basename(path: string): string {
  return path.split('/').pop() ?? path
}

// Resolve a citation/source-note path back to one of this turn's retrieved
// sources so the click can open the full document. Matches on full path first,
// then filename, since the model often cites by basename alone.
function matchSource(path: string): SourceReference | undefined {
  const lower = path.toLowerCase()
  const base = basename(path).toLowerCase()
  return props.sources?.find(
    (source) =>
      source.path.toLowerCase() === lower ||
      basename(source.path).toLowerCase() === base,
  )
}

// Event delegation: inline citation chips and the source-note line live inside
// v-html, so they carry a data-path rather than a Vue listener.
function onContentClick(event: MouseEvent) {
  const origin = event.target as HTMLElement | null
  const node = origin?.closest('[data-path]') as HTMLElement | null
  const path = node?.getAttribute('data-path')
  if (!path) return
  const source = matchSource(path)
  if (source !== undefined) viewer.show(source)
}
</script>

<template>
  <div class="assistant-turn">
    <header class="assistant-turn__head">
      <div class="assistant-turn__identity">
        <span class="assistant-turn__role calliope-serif">{{ displayRole(role) }}</span>
        <span v-if="role === 'search'" class="assistant-turn__tag calliope-mono">retrieval</span>
      </div>
      <CopyMessageButton :content="content" />
    </header>
    <!-- Assistant output is LLM-authored markdown; renderMarkdown sanitizes before v-html. -->
    <div
      class="assistant-turn__content markdown-body"
      @click="onContentClick"
      v-html="renderedContent"
    />
    <!-- Overflow suppresses the truncation notice: when the prompt itself was cut,
         "raise Max tokens" is counterproductive advice (it shrinks the prompt budget). -->
    <div v-if="contextOverflow" class="assistant-turn__notice" role="status">
      <span class="calliope-eyebrow assistant-turn__notice-label">Context overflow</span>
      <p class="assistant-turn__notice-body">
        The request exceeded the model's context window, so the server dropped part of the
        prompt before generating — this response may ignore canon or instructions. Detach or
        shorten cited documents, or run the model server with a larger context size (and
        raise <strong>CALLIOPE_DEFAULT_NUM_CTX</strong> to match).
      </p>
    </div>
    <div v-else-if="truncated" class="assistant-turn__notice" role="status">
      <span class="calliope-eyebrow assistant-turn__notice-label">Truncated</span>
      <p class="assistant-turn__notice-body">
        This response hit the model's length limit and may be cut off. Raise
        <strong>Max tokens</strong> for this profile in Settings to generate the full document.
      </p>
    </div>
    <div v-if="sources && sources.length > 0" class="assistant-turn__sources">
      <span class="calliope-eyebrow assistant-turn__sources-label">Sources</span>
      <div class="assistant-turn__source-list">
        <SourceChip
          v-for="source in sources"
          :key="source.chunk_id"
          :source="source"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.assistant-turn {
  justify-self: stretch;
  max-width: 44rem;
  display: flex;
  flex-direction: column;
  gap: var(--calliope-space-sm);
}

.assistant-turn__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--calliope-space-xs);
}

.assistant-turn__identity {
  display: flex;
  align-items: baseline;
  gap: var(--calliope-space-xs);
  min-width: 0;
}

.assistant-turn__role {
  font-size: 0.95rem;
  font-weight: 420;
  color: var(--calliope-bronze);
  letter-spacing: -0.005em;
}

.assistant-turn__tag {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.22em;
  color: var(--calliope-paper-dim);
}

.assistant-turn__content {
  margin: 0;
  color: var(--calliope-paper);
  font-family: var(--calliope-font-chat);
  font-size: 0.965rem;
  line-height: 1.7;
  /* min-width lets overflowing children (code blocks, tables) scroll instead of stretching the column */
  min-width: 0;
}

/* Rendered markdown — typeset to the editorial system rather than browser defaults.
   Selectors use :deep() because v-html content carries no scoped-style attribute. */

/* Illuminated drop-cap on the first paragraph — implemented directly here
   because the <p> lives inside v-html and cannot receive a class attribute. */
.markdown-body :deep(> p:first-child::first-letter) {
  font-family: var(--calliope-font-display);
  font-size: 3.2em;
  font-weight: 380;
  line-height: 0.82;
  float: left;
  margin-right: 0.06em;
  margin-top: 0.04em;
  color: var(--calliope-bronze);
  text-shadow:
    0 0 18px var(--calliope-bronze-glow),
    0 0 36px var(--calliope-bronze-veil);
}

/* Reduced-motion: flatten the glow bloom on the drop cap */
@media (prefers-reduced-motion: reduce) {
  .markdown-body :deep(> p:first-child::first-letter) {
    text-shadow: none;
  }
}

.markdown-body :deep(> :first-child) {
  margin-top: 0;
}

.markdown-body :deep(> :last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(p) {
  margin: 0 0 0.85em;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  font-family: var(--calliope-font-display);
  font-weight: 460;
  color: var(--calliope-paper);
  letter-spacing: -0.012em;
  line-height: 1.2;
  margin: 1.35em 0 0.55em;
}

.markdown-body :deep(h1) {
  font-size: 1.4rem;
}

.markdown-body :deep(h2) {
  font-size: 1.22rem;
}

.markdown-body :deep(h3) {
  font-size: 1.08rem;
}

.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  font-size: 0.98rem;
}

.markdown-body :deep(strong) {
  font-weight: 600;
  color: var(--calliope-paper);
}

.markdown-body :deep(em) {
  font-style: italic;
}

.markdown-body :deep(a) {
  color: var(--calliope-bronze);
  text-decoration: none;
  border-bottom: 1px solid var(--calliope-bronze-glow);
  transition:
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.markdown-body :deep(a:hover) {
  color: var(--calliope-bronze-deep);
  border-bottom-color: var(--calliope-bronze);
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0 0 0.85em;
  padding-left: 1.4em;
}

.markdown-body :deep(li) {
  margin-bottom: 0.3em;
}

.markdown-body :deep(li::marker) {
  color: var(--calliope-paper-dim);
}

.markdown-body :deep(li > ul),
.markdown-body :deep(li > ol) {
  margin: 0.3em 0 0;
}

.markdown-body :deep(blockquote) {
  margin: 0 0 0.85em;
  padding: 0.15em 0 0.15em 1em;
  border-left: 2px solid var(--calliope-bronze);
  color: var(--calliope-paper-muted);
  font-style: italic;
}

.markdown-body :deep(blockquote > :last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(code) {
  font-family: var(--calliope-font-mono);
  font-size: 0.86em;
  background: var(--calliope-ink-raised);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-xs);
  padding: 0.08em 0.36em;
}

.markdown-body :deep(pre) {
  margin: 0 0 0.85em;
  padding: 0.85rem 1rem;
  background: var(--calliope-ink);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-sm);
  overflow-x: auto;
}

.markdown-body :deep(pre code) {
  font-size: 0.82rem;
  line-height: 1.6;
  background: none;
  border: none;
  border-radius: 0;
  padding: 0;
}

.markdown-body :deep(hr) {
  margin: 1.2em 0;
  border: none;
  border-top: 1px solid var(--calliope-border);
}

.markdown-body :deep(table) {
  margin: 0 0 0.85em;
  border-collapse: collapse;
  font-size: 0.9em;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 0.4em 0.7em;
  border: 1px solid var(--calliope-border);
  text-align: left;
}

.markdown-body :deep(th) {
  font-weight: 600;
  color: var(--calliope-paper);
  background: var(--calliope-overlay-hover);
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: var(--calliope-radius-sm);
}

/* Inline source citations — the model emits "(path.md; other.md)" in prose;
   markdown.ts rewrites each into a tag that flows within the line. */
.markdown-body :deep(.md-citation) {
  display: inline;
}

.markdown-body :deep(.md-citation__item) {
  display: inline-flex;
  align-items: center;
  gap: 0.32em;
  margin: 0 0.12em;
  padding: 0.1em 0.55em 0.1em 0.45em;
  font-family: var(--calliope-font-mono);
  font-size: 0.74em;
  line-height: 1.3;
  letter-spacing: 0.01em;
  color: var(--calliope-bronze);
  background: var(--calliope-bronze-veil);
  border: 1px solid var(--calliope-bronze-glow);
  border-radius: var(--calliope-radius-pill);
  vertical-align: -0.16em;
  cursor: pointer;
  transition:
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.markdown-body :deep(.md-citation__item::before) {
  content: '';
  flex: none;
  width: 0.85em;
  height: 0.85em;
  background-color: currentColor;
  -webkit-mask: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%3E%3Cpath%20d='M13%209V3.5L18.5%209M6%202c-1.1%200-2%20.9-2%202v16a2%202%200%200%200%202%202h12a2%202%200%200%200%202-2V8l-6-6H6z'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%3E%3Cpath%20d='M13%209V3.5L18.5%209M6%202c-1.1%200-2%20.9-2%202v16a2%202%200%200%200%202%202h12a2%202%200%200%200%202-2V8l-6-6H6z'/%3E%3C/svg%3E") center / contain no-repeat;
}

.markdown-body :deep(.md-citation__item:hover) {
  color: var(--calliope-bronze-deep);
  background: var(--calliope-bronze-glow);
  border-color: var(--calliope-bronze);
}

/* Source attribution line — the model emits "*Source: file.md (Section …)*";
   markdown.ts lifts it into a styled, clickable footnote rather than bare italic.
   A gilt left-rule and a small-caps label set it apart as editorial apparatus. */
.markdown-body :deep(.md-source) {
  display: inline-flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 0.4em;
  margin-top: 0.25em;
  padding: 0.2em 0.7em 0.2em 0.65em;
  border-left: 2px solid var(--calliope-bronze);
  border-radius: 0 var(--calliope-radius-sm) var(--calliope-radius-sm) 0;
  background: var(--calliope-bronze-veil);
  font-style: normal;
  cursor: pointer;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-fast) var(--calliope-ease-out);
}

.markdown-body :deep(.md-source::before) {
  content: '';
  align-self: center;
  flex: none;
  width: 0.95em;
  height: 0.95em;
  background-color: var(--calliope-bronze);
  -webkit-mask: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%3E%3Cpath%20d='M18%202H6a2%202%200%200%200-2%202v16l4-2%204%202%204-2%204%202V4a2%202%200%200%200-2-2m-1%2010H7v-2h10m0-3H7V7h10z'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%3E%3Cpath%20d='M18%202H6a2%202%200%200%200-2%202v16l4-2%204%202%204-2%204%202V4a2%202%200%200%200-2-2m-1%2010H7v-2h10m0-3H7V7h10z'/%3E%3C/svg%3E") center / contain no-repeat;
}

.markdown-body :deep(.md-source:hover) {
  background: var(--calliope-bronze-glow);
  box-shadow: inset 2px 0 0 var(--calliope-bronze-deep);
}

.markdown-body :deep(.md-source__label) {
  font-family: var(--calliope-font-mono);
  font-size: 0.62em;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: var(--calliope-bronze);
}

.markdown-body :deep(.md-source__ref) {
  font-family: var(--calliope-font-mono);
  font-size: 0.82em;
  letter-spacing: 0.01em;
  color: var(--calliope-paper);
}

.markdown-body :deep(.md-source__loc) {
  font-size: 0.82em;
  color: var(--calliope-paper-muted);
  font-style: italic;
}

.assistant-turn__notice {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  margin-top: var(--calliope-space-2xs);
  padding: 0.6rem 0.8rem;
  border: 1px solid var(--calliope-bronze-glow);
  border-left: 2px solid var(--calliope-bronze);
  border-radius: var(--calliope-radius-md);
  background: var(--calliope-bronze-veil);
}

.assistant-turn__notice-label {
  color: var(--calliope-bronze);
  font-size: 0.6rem;
  letter-spacing: 0.22em;
}

.assistant-turn__notice-body {
  margin: 0;
  color: var(--calliope-paper-muted);
  font-size: 0.82rem;
  line-height: 1.55;
}

.assistant-turn__notice-body strong {
  color: var(--calliope-paper);
  font-weight: 600;
}

.assistant-turn__sources {
  margin-top: var(--calliope-space-sm);
  display: flex;
  flex-direction: column;
  gap: var(--calliope-space-xs);
}

.assistant-turn__sources-label {
  color: var(--calliope-paper-dim);
  font-size: 0.6rem;
  letter-spacing: 0.22em;
}

.assistant-turn__source-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
</style>
