<script setup lang="ts">
import type { SourceReference } from '../types'
import { useSourceViewerStore } from '../stores/sourceViewerStore'

const props = defineProps<{
  source: SourceReference
}>()

const viewer = useSourceViewerStore()

function filename(path: string): string {
  const parts = path.split('/')
  return parts[parts.length - 1] ?? path
}

function open() {
  viewer.show(props.source)
}
</script>

<template>
  <button
    type="button"
    class="source-chip"
    :aria-label="`Open source ${filename(source.path)}`"
    @click="open"
  >
    <span class="source-chip__head">
      <span class="source-chip__path calliope-mono">{{ filename(source.path) }}</span>
      <span v-if="source.heading" class="source-chip__heading calliope-mono">
        · {{ source.heading }}
      </span>
      <span class="source-chip__score calliope-mono">
        {{ (source.score * 100).toFixed(0) }}%
      </span>
      <v-icon
        class="source-chip__open"
        icon="$mdi-arrow-expand"
        size="13"
        aria-hidden="true"
      />
    </span>
    <span class="source-chip__excerpt">{{ source.context }}</span>
  </button>
</template>

<style scoped>
/* Editorial footnote card — opens the full source document on click. */
.source-chip {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 1px solid var(--calliope-bronze-veil);
  border-radius: var(--calliope-radius-md);
  padding: 0.5rem 0.8rem;
  cursor: pointer;
  font: inherit;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    transform var(--calliope-duration-fast) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-fast) var(--calliope-ease-out);
}

.source-chip:hover {
  background: var(--calliope-bronze-veil);
  border-color: var(--calliope-bronze);
  box-shadow: 0 0 0 1px var(--calliope-bronze-glow);
}

.source-chip:active {
  transform: translateY(1px);
}

.source-chip:focus-visible {
  outline: none;
  border-color: var(--calliope-bronze);
  box-shadow: 0 0 0 3px var(--calliope-bronze-veil);
}

.source-chip__head {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.7rem;
  color: var(--calliope-paper-muted);
  letter-spacing: 0.02em;
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

.source-chip__open {
  color: var(--calliope-paper-dim);
  opacity: 0;
  transition:
    opacity var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.source-chip:hover .source-chip__open,
.source-chip:focus-visible .source-chip__open {
  opacity: 1;
  color: var(--calliope-bronze);
}

.source-chip__excerpt {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0.5rem 0 0;
  color: var(--calliope-paper-muted);
  font-size: 0.82rem;
  line-height: 1.55;
}
</style>
