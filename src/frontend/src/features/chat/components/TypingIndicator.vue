<script setup lang="ts">
</script>

<template>
  <div class="typing-indicator" role="status" aria-label="Calliope is thinking">
    <span class="typing-indicator__role calliope-serif">Calliope</span>
    <span class="typing-indicator__dots" aria-hidden="true">
      <span class="typing-indicator__dot" />
      <span class="typing-indicator__dot" />
      <span class="typing-indicator__dot" />
    </span>
  </div>
</template>

<style scoped>
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}

.typing-indicator__role {
  color: var(--calliope-bronze);
  font-size: 0.95rem;
  letter-spacing: -0.005em;
}

.typing-indicator__dots {
  display: inline-flex;
  align-items: center;
  gap: 0.32rem;
}

.typing-indicator__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--calliope-bronze);
  opacity: 0.35;
  animation: calliope-typing 1.2s var(--calliope-ease-in-out) infinite;
}

.typing-indicator__dot:nth-child(2) {
  animation-delay: 160ms;
}

.typing-indicator__dot:nth-child(3) {
  animation-delay: 320ms;
}

@keyframes calliope-typing {
  0%, 80%, 100% {
    opacity: 0.25;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-2px);
  }
}
</style>
