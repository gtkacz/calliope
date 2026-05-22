<script setup lang="ts">
defineProps<{
  content: string
}>()
</script>

<template>
  <div class="message-bubble">
    <span class="message-bubble__role calliope-eyebrow">You</span>
    <p class="message-bubble__content">{{ content }}</p>
  </div>
</template>

<style scoped>
.message-bubble {
  justify-self: end;
  max-width: 38rem;
  padding: 1rem 1.15rem 1.05rem;
  background: var(--calliope-ink-raised);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-lg);
  border-bottom-right-radius: var(--calliope-radius-xs);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.message-bubble__role {
  color: var(--calliope-paper-dim);
  font-size: 0.62rem;
  letter-spacing: 0.22em;
}

.message-bubble__content {
  margin: 0;
  color: var(--calliope-paper);
  font-family: var(--calliope-font-chat);
  font-size: 0.95rem;
  line-height: 1.62;
  white-space: pre-wrap;
}
</style>
