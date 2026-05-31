<script setup lang="ts">
import type { SourceReference } from '../types'

defineProps<{
  source: SourceReference
}>()

function filename(path: string): string {
  const parts = path.split('/')
  return parts[parts.length - 1] ?? path
}
</script>

<template>
  <details class="source-chip">
    <summary class="source-chip__head">
      <span class="source-chip__path calliope-mono">{{ filename(source.path) }}</span>
      <span v-if="source.heading" class="source-chip__heading calliope-mono">
        · {{ source.heading }}
      </span>
      <span class="source-chip__score calliope-mono">
        {{ (source.score * 100).toFixed(0) }}%
      </span>
    </summary>
    <p class="source-chip__excerpt">{{ source.excerpt }}</p>
  </details>
</template>

<style scoped>
/* Editorial footnote pill — hairline gilt border, no filled background at rest */
.source-chip {
  display: block;
  background: transparent;
  border: 1px solid var(--calliope-bronze-veil);
  border-radius: var(--calliope-radius-md);
  padding: 0.45rem 0.75rem;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.source-chip:hover {
  background: var(--calliope-bronze-veil);
  border-color: var(--calliope-bronze);
}

.source-chip[open] {
  background: var(--calliope-bronze-veil);
  border-color: var(--calliope-bronze);
}

.source-chip__head {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
  cursor: pointer;
  list-style: none;
  font-size: 0.7rem;
  color: var(--calliope-paper-muted);
  letter-spacing: 0.02em;
}

.source-chip__head::-webkit-details-marker {
  display: none;
}

/* Doc icon rendered as a CSS mask so it inherits the gilt colour token */
.source-chip__head::before {
  content: '';
  flex: none;
  width: 0.8em;
  height: 0.8em;
  background-color: var(--calliope-bronze);
  -webkit-mask: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%3E%3Cpath%20d='M13%209V3.5L18.5%209M6%202c-1.1%200-2%20.9-2%202v16a2%202%200%200%200%202%202h12a2%202%200%200%200%202-2V8l-6-6H6z'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%3E%3Cpath%20d='M13%209V3.5L18.5%209M6%202c-1.1%200-2%20.9-2%202v16a2%202%200%200%200%202%202h12a2%202%200%200%200%202-2V8l-6-6H6z'/%3E%3C/svg%3E") center / contain no-repeat;
  align-self: center;
}

.source-chip__path {
  color: var(--calliope-bronze);
  font-weight: 500;
}

.source-chip__heading {
  color: var(--calliope-paper-dim);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.source-chip__score {
  margin-left: auto;
  color: var(--calliope-bronze);
  font-size: 0.66rem;
  letter-spacing: 0.06em;
}

.source-chip__excerpt {
  margin: 0.6rem 0 0;
  padding-top: 0.6rem;
  border-top: 1px solid var(--calliope-bronze-veil);
  color: var(--calliope-paper-muted);
  font-size: 0.83rem;
  line-height: 1.6;
  white-space: pre-wrap;
}
</style>
