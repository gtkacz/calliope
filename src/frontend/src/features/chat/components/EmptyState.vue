<script setup lang="ts">
</script>

<template>
  <section class="empty-state">
    <span class="calliope-eyebrow empty-state__eyebrow">A new thread</span>
    <h1 class="calliope-display-lg empty-state__title">
      Start a conversation, or ask the library.
    </h1>
    <p class="empty-state__body">
      Calliope reads your workspace notes so each reply is grounded in what you&rsquo;ve already
      written. Toggle <span class="calliope-mono">Search</span> in the composer to retrieve passages
      without generating a turn.
    </p>
  </section>
</template>

<style scoped>
.empty-state {
  margin: auto;
  max-width: 38rem;
  padding: 4rem 2.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.empty-state__eyebrow {
  color: var(--calliope-paper-dim);
}

.empty-state__title {
  margin: 0;
  color: var(--calliope-paper);
}

.empty-state__body {
  margin: 0;
  max-width: 32rem;
  color: var(--calliope-paper-muted);
  font-size: 0.97rem;
  line-height: 1.7;
}

.empty-state__body .calliope-mono {
  color: var(--calliope-bronze);
  font-size: 0.88rem;
}
</style>
