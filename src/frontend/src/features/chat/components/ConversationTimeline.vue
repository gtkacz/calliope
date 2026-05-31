<script setup lang="ts">
import { Motion } from 'motion-v'

import type { MessageRead, SourceReference } from '../types'
import AssistantTurn from './AssistantTurn.vue'
import EmptyState from './EmptyState.vue'
import MessageBubble from './MessageBubble.vue'
import TypingIndicator from './TypingIndicator.vue'

defineProps<{
  messages: MessageRead[]
  pending: boolean
  errorMessage: string | null
}>()

function sourcesFor(message: MessageRead): SourceReference[] {
  const sources = message.metadata.sources
  return Array.isArray(sources) ? (sources as SourceReference[]) : []
}
</script>

<template>
  <div
    class="timeline calliope-manuscript-ruling calliope-reading-vignette"
    :class="{ 'is-empty': messages.length === 0 }"
  >
    <EmptyState v-if="messages.length === 0 && !pending && !errorMessage" />

    <template v-for="(message, index) in messages" :key="message.id">
      <!-- Gilt hairline section-break rule between every consecutive pair of turns -->
      <hr v-if="index > 0" class="timeline__turn-rule calliope-turn-rule" aria-hidden="true" />

      <Motion
        tag="article"
        class="timeline__row"
        :initial="{ opacity: 0, scale: 0.98, y: 4 }"
        :animate="{ opacity: 1, scale: 1, y: 0 }"
        :transition="{ type: 'spring', stiffness: 280, damping: 26, mass: 0.6 }"
      >
        <MessageBubble v-if="message.role === 'user'" :content="message.content" />
        <AssistantTurn
          v-else
          :role="message.role"
          :content="message.content"
          :sources="sourcesFor(message)"
        />
      </Motion>
    </template>

    <Motion
      v-if="pending"
      class="timeline__row"
      :initial="{ opacity: 0, y: 4 }"
      :animate="{ opacity: 1, y: 0 }"
      :transition="{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }"
    >
      <TypingIndicator />
    </Motion>

    <div v-if="errorMessage" class="timeline__error">
      <span class="calliope-eyebrow timeline__error-label">Error</span>
      <p class="timeline__error-body">{{ errorMessage }}</p>
    </div>
  </div>
</template>

<style scoped>
.timeline {
  position: relative;
  display: grid;
  align-content: start;
  gap: var(--calliope-space-lg);
  padding: var(--calliope-space-xl) var(--calliope-space-xl) var(--calliope-space-lg);
  overflow: auto;
  max-width: 80%;
  margin: 0 auto;
}

.timeline.is-empty {
  align-content: center;
}

.timeline__row {
  display: grid;
  width: 100%;
  position: relative;
  z-index: 2;
}

/* Gilt hairline turn-rule between conversation turns */
.timeline__turn-rule {
  height: 1px;
  border: none;
  margin: 0;
  background: linear-gradient(
    to right,
    transparent 0%,
    var(--calliope-rule, var(--calliope-bronze)) 35%,
    var(--calliope-rule, var(--calliope-bronze)) 65%,
    transparent 100%
  );
  opacity: 0.35;
}

.timeline__error {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  max-width: 38rem;
  padding: 0.85rem 1rem;
  border: 1px solid var(--calliope-warm-error-soft);
  border-left: 2px solid var(--calliope-warm-error);
  border-radius: var(--calliope-radius-md);
  background: var(--calliope-warm-error-veil);
}

.timeline__error-label {
  color: var(--calliope-warm-error);
  letter-spacing: 0.22em;
}

.timeline__error-body {
  margin: 0;
  color: var(--calliope-paper);
  font-size: 0.9rem;
  line-height: 1.6;
}
</style>
