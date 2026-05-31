<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{
  // Epoch milliseconds when the current request began; null when idle.
  since?: number | null
}>()

// A reactive clock that only ticks while a request is in flight. Decoupling the
// tick source from the prop lets the formatted value update ~10×/sec without the
// parent re-rendering.
const now = ref(Date.now())
let intervalId: ReturnType<typeof setInterval> | null = null

function stopTicking() {
  if (intervalId !== null) {
    clearInterval(intervalId)
    intervalId = null
  }
}

function startTicking() {
  stopTicking()
  now.value = Date.now()
  intervalId = setInterval(() => {
    now.value = Date.now()
  }, 100)
}

watch(
  () => props.since,
  (value) => {
    if (typeof value === 'number') {
      startTicking()
    } else {
      stopTicking()
    }
  },
  { immediate: true },
)

onBeforeUnmount(stopTicking)

const elapsedLabel = computed(() => {
  if (typeof props.since !== 'number') return ''
  const elapsedMs = Math.max(0, now.value - props.since)
  if (elapsedMs < 60_000) {
    return `${(elapsedMs / 1000).toFixed(1)}s`
  }
  const totalSeconds = Math.floor(elapsedMs / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
})
</script>

<template>
  <div class="typing-indicator" role="status" aria-label="Calliope is thinking">
    <span class="typing-indicator__role calliope-serif">
      Calliope<span class="typing-indicator__dots" aria-hidden="true">
        <span class="typing-indicator__dot" />
        <span class="typing-indicator__dot" />
        <span class="typing-indicator__dot" />
      </span>
    </span>
    <span
      v-if="elapsedLabel"
      class="typing-indicator__elapsed calliope-mono"
      aria-hidden="true"
    >{{ elapsedLabel }}</span>
  </div>
</template>

<style scoped>
.typing-indicator {
  display: flex;
  align-items: baseline;
  gap: 0.45rem;
}

.typing-indicator__role {
  display: inline-flex;
  align-items: baseline;
  color: var(--calliope-bronze);
  font-size: 0.95rem;
  letter-spacing: -0.005em;
}

.typing-indicator__dots {
  display: inline-flex;
  align-items: flex-end;
  gap: 0.14rem;
  margin-left: 0.16rem;
  transform: translateY(0.03em);
}

.typing-indicator__elapsed {
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  color: var(--calliope-paper-dim);
  /* Fixed-width feel so the ticking decimal does not jitter neighbouring layout */
  font-variant-numeric: tabular-nums;
}

.typing-indicator__dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--calliope-bronze);
  opacity: 0.35;
  /* box-shadow applies the warm gilt glow bloom at peak opacity */
  box-shadow: 0 0 0 0 var(--calliope-bronze-glow);
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
    box-shadow: 0 0 0 0 var(--calliope-bronze-glow);
  }
  40% {
    opacity: 1;
    transform: translateY(-2px);
    /* Warm glow bloom radiates outward at the apex of each bounce */
    box-shadow: 0 0 8px 3px var(--calliope-bronze-glow);
  }
}

/* No animation for reduced-motion users; fade only, no glow */
@media (prefers-reduced-motion: reduce) {
  .typing-indicator__dot {
    animation: calliope-typing-fade 1.2s var(--calliope-ease-in-out) infinite;
    box-shadow: none;
  }

  @keyframes calliope-typing-fade {
    0%, 80%, 100% { opacity: 0.25; }
    40% { opacity: 1; }
  }
}
</style>
