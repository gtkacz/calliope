<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'

defineProps<{
  content: string
}>()

const copied = ref(false)
let toastTimeout: ReturnType<typeof setTimeout> | null = null

async function copyMessage(content: string) {
  try {
    await navigator.clipboard.writeText(content)
    copied.value = true
    if (toastTimeout !== null) clearTimeout(toastTimeout)
    toastTimeout = setTimeout(() => {
      copied.value = false
      toastTimeout = null
    }, 1600)
  } catch {
    // Clipboard access can fail outside secure contexts; leave the message intact.
  }
}

onBeforeUnmount(() => {
  if (toastTimeout !== null) clearTimeout(toastTimeout)
})
</script>

<template>
  <v-tooltip text="Copy message" location="top" :open-delay="200">
    <template #activator="{ props: tipProps }">
      <button
        v-bind="tipProps"
        type="button"
        class="copy-message-button"
        aria-label="Copy message"
        @click="copyMessage(content)"
      >
        <v-icon icon="$mdi-content-copy" size="15" />
      </button>
    </template>
  </v-tooltip>

  <div
    v-if="copied"
    class="copy-message-toast calliope-mono"
    role="status"
    aria-live="polite"
  >
    Copied to clipboard
  </div>
</template>

<style scoped>
.copy-message-button {
  flex: none;
  width: 1.75rem;
  height: 1.75rem;
  display: inline-grid;
  place-items: center;
  border: 1px solid transparent;
  border-radius: var(--calliope-radius-sm);
  background: transparent;
  color: var(--calliope-paper-dim);
  cursor: pointer;
  opacity: 0.72;
  transition:
    opacity var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.copy-message-button:hover,
.copy-message-button:focus-visible {
  opacity: 1;
  color: var(--calliope-bronze);
  background: var(--calliope-overlay-hover);
  border-color: var(--calliope-border);
  outline: none;
}

.copy-message-toast {
  position: fixed;
  left: 50%;
  bottom: 1.25rem;
  z-index: 4000;
  transform: translateX(-50%);
  padding: 0.48rem 0.75rem;
  border: 1px solid var(--calliope-border-strong);
  border-radius: var(--calliope-radius-pill);
  background: var(--calliope-ink-top);
  color: var(--calliope-paper);
  box-shadow: var(--calliope-shadow-rest);
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  pointer-events: none;
}
</style>
