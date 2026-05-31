<script setup lang="ts">
import { Motion, useReducedMotion } from 'motion-v'

const emit = defineEmits<{
  'select-seed': [prompt: string]
}>()

// When reduced motion is preferred, skip the entrance offset entirely so the
// content renders at its resting (visible) state rather than depending on the
// animation to fade it in.
const reduced = useReducedMotion()

const seeds = [
  { icon: '$mdi-book-open-page-variant-outline', label: 'Explore notes', prompt: 'What themes recur across my recent notes?' },
  { icon: '$mdi-lightbulb-outline', label: 'Synthesise ideas', prompt: 'Connect the ideas I’ve been developing this week.' },
  { icon: '$mdi-magnify', label: 'Search passages', prompt: 'Find every mention of the protagonist’s motivation.' },
  { icon: '$mdi-feather', label: 'Draft with me', prompt: 'Help me write the next scene in my current chapter.' },
]
</script>

<template>
  <section class="empty-state" aria-label="Start a new conversation">
    <Motion
      tag="div"
      class="empty-state__hero"
      :initial="reduced ? false : { opacity: 0, y: 16 }"
      :animate="{ opacity: 1, y: 0 }"
      :transition="{ duration: 0.48, ease: [0.16, 1, 0.3, 1] }"
    >
      <span class="calliope-eyebrow empty-state__eyebrow">A new tale begins</span>
      <h1 class="calliope-display-lg empty-state__title">
        What shall we write today?
      </h1>
      <p class="empty-state__body">
        Calliope reads your workspace notes so every reply is grounded in what you&rsquo;ve
        already written. Toggle <span class="calliope-mono empty-state__mode-label">Search</span>
        in the composer to retrieve passages without generating a turn.
      </p>
    </Motion>

    <Motion
      tag="div"
      class="empty-state__seeds"
      :initial="reduced ? false : { opacity: 0, y: 12 }"
      :animate="{ opacity: 1, y: 0 }"
      :transition="{ duration: 0.42, delay: 0.16, ease: [0.16, 1, 0.3, 1] }"
    >
      <Motion
        v-for="(seed, i) in seeds"
        :key="seed.label"
        tag="button"
        type="button"
        class="empty-state__seed"
        :initial="reduced ? false : { opacity: 0, y: 8 }"
        :animate="{ opacity: 1, y: 0 }"
        :while-hover="{ y: -2 }"
        :while-press="{ scale: 0.98 }"
        :transition="{ duration: 0.32, delay: 0.2 + i * 0.06, ease: [0.16, 1, 0.3, 1] }"
        @click="emit('select-seed', seed.prompt)"
      >
        <span class="empty-state__seed-icon" aria-hidden="true">
          <v-icon :icon="seed.icon" size="18" />
        </span>
        <span class="empty-state__seed-label calliope-eyebrow">{{ seed.label }}</span>
        <span class="empty-state__seed-prompt calliope-serif">{{ seed.prompt }}</span>
      </Motion>
    </Motion>
  </section>
</template>

<style scoped>
.empty-state {
  margin: auto;
  max-width: 44rem;
  width: 100%;
  padding: var(--calliope-space-2xl) var(--calliope-space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--calliope-space-xl);
  /* Sits above the manuscript ruling and vignette pseudo-elements in chat-body */
  position: relative;
  z-index: 2;
}

.empty-state__hero {
  display: flex;
  flex-direction: column;
  gap: var(--calliope-space-sm);
}

.empty-state__eyebrow {
  /* Gilt colour on the eyebrow to immediately establish the Scriptorium palette */
  color: var(--calliope-bronze);
  letter-spacing: 0.22em;
}

.empty-state__title {
  margin: 0;
  color: var(--calliope-paper);
}

.empty-state__body {
  margin: 0;
  max-width: 34rem;
  color: var(--calliope-paper-muted);
  font-size: 0.97rem;
  line-height: 1.72;
}

/* Inline mode label styled as an editorial annotation */
.empty-state__mode-label {
  color: var(--calliope-bronze);
  font-size: 0.85em;
  padding: 0.05em 0.35em;
  background: var(--calliope-bronze-veil);
  border: 1px solid var(--calliope-bronze-veil);
  border-radius: var(--calliope-radius-xs);
}

.empty-state__seeds {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--calliope-space-sm);
}

@media (max-width: 640px) {
  .empty-state__seeds {
    grid-template-columns: 1fr;
  }
}

.empty-state__seed {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--calliope-space-xs);
  padding: var(--calliope-space-md);
  background: var(--calliope-ink-raised);
  border: 1px solid var(--calliope-border-strong);
  border-radius: var(--calliope-radius-lg);
  text-align: left;
  box-shadow: var(--calliope-shadow-rest);
  /* Reset native button chrome so the seed reads as an editorial card */
  font: inherit;
  width: 100%;
  cursor: pointer;
  transition:
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-base) var(--calliope-ease-out);
}

.empty-state__seed:hover {
  border-color: var(--calliope-bronze);
  background: var(--calliope-overlay-active);
  box-shadow:
    var(--calliope-shadow-rest),
    0 0 18px -2px var(--calliope-bronze-glow);
}

.empty-state__seed:focus-visible {
  outline: 2px solid var(--calliope-bronze);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .empty-state__seed {
    transition: none;
  }
}

.empty-state__seed-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--calliope-radius-sm);
  background: var(--calliope-bronze-veil);
  color: var(--calliope-bronze);
}

.empty-state__seed-label {
  color: var(--calliope-bronze);
  /* Override eyebrow muted colour so labels read as gilt annotations */
  letter-spacing: 0.16em;
}

.empty-state__seed-prompt {
  font-size: 0.875rem;
  color: var(--calliope-paper-muted);
  line-height: 1.55;
  letter-spacing: -0.003em;
}
</style>
