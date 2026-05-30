<script setup lang="ts">
import { computed } from 'vue'

import { renderMarkdown } from '@/shared/markdown'

import type { SourceReference } from '../types'
import SourceChip from './SourceChip.vue'

const props = defineProps<{
  role: string
  content: string
  sources?: SourceReference[]
}>()

const renderedContent = computed<string>(() => renderMarkdown(props.content))

function displayRole(role: string): string {
  if (role === 'assistant') return 'Calliope'
  if (role === 'search') return 'Search'
  return role.charAt(0).toUpperCase() + role.slice(1)
}
</script>

<template>
  <div class="assistant-turn">
    <header class="assistant-turn__head">
      <span class="assistant-turn__role calliope-serif">{{ displayRole(role) }}</span>
      <span v-if="role === 'search'" class="assistant-turn__tag calliope-mono">retrieval</span>
    </header>
    <!-- Assistant output is LLM-authored markdown; renderMarkdown sanitizes before v-html. -->
    <div class="assistant-turn__content markdown-body" v-html="renderedContent" />
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
  gap: 0.65rem;
}

.assistant-turn__head {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
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

.assistant-turn__sources {
  margin-top: 0.65rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
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
