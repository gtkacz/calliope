<script setup lang="ts">
defineProps<{
  content: string
}>()

async function copyMessage(content: string) {
  try {
    await navigator.clipboard.writeText(content)
  } catch {
    // Clipboard access can fail outside secure contexts; leave the message intact.
  }
}
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
</style>
