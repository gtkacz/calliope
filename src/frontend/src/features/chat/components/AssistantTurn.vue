<script setup lang="ts">
import type { SourceReference } from '../types'
import SourceChip from './SourceChip.vue'

defineProps<{
  role: string
  content: string
  sources?: SourceReference[]
}>()

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
    <p class="assistant-turn__content">{{ content }}</p>
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
  font-size: 0.965rem;
  line-height: 1.7;
  white-space: pre-wrap;
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
