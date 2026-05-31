<script setup lang="ts">
import type { MessageRead, SourceReference } from "../types";
import AssistantTurn from "./AssistantTurn.vue";
import MessageBubble from "./MessageBubble.vue";
import TypingIndicator from "./TypingIndicator.vue";

defineProps<{
  messages: MessageRead[];
  pending: boolean;
  pendingSince: number | null;
  errorMessage: string | null;
}>();

function sourcesFor(message: MessageRead): SourceReference[] {
  const sources = message.metadata.sources;
  return Array.isArray(sources) ? (sources as SourceReference[]) : [];
}

function truncatedFor(message: MessageRead): boolean {
  return message.metadata.truncated === true;
}
</script>

<template>
  <div class="write-thread">
    <div class="write-thread__scroll">
      <div v-if="messages.length === 0 && !pending && !errorMessage" class="write-thread__empty">
        <p class="calliope-eyebrow write-thread__empty-label">Iterations</p>
        <p class="write-thread__empty-body">
          Send a message to start iterating on the canvas.
        </p>
      </div>

      <template v-for="message in messages" :key="message.id">
        <div class="write-thread__row">
          <MessageBubble v-if="message.role === 'user'" :content="message.content" />
          <AssistantTurn
            v-else
            :role="message.role"
            :content="message.content"
            :sources="sourcesFor(message)"
            :truncated="truncatedFor(message)"
          />
        </div>
      </template>

      <div v-if="pending" class="write-thread__row">
        <TypingIndicator :since="pendingSince" />
      </div>

      <div v-if="errorMessage" class="write-thread__error">
        <span class="calliope-eyebrow write-thread__error-label">Error</span>
        <p class="write-thread__error-body">{{ errorMessage }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.write-thread {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  background: var(--calliope-ink-soft);
}

.write-thread__scroll {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--calliope-space-md);
  padding: var(--calliope-space-md);
}

.write-thread__row {
  display: grid;
  width: 100%;
}

.write-thread__empty {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin: auto;
  text-align: center;
  padding: var(--calliope-space-xl);
}

.write-thread__empty-label {
  color: var(--calliope-paper-dim);
}

.write-thread__empty-body {
  margin: 0;
  color: var(--calliope-paper-muted);
  font-size: 0.85rem;
  line-height: 1.6;
}

.write-thread__error {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.75rem 0.85rem;
  border: 1px solid var(--calliope-warm-error-soft);
  border-left: 2px solid var(--calliope-warm-error);
  border-radius: var(--calliope-radius-md);
  background: var(--calliope-warm-error-veil);
}

.write-thread__error-label {
  color: var(--calliope-warm-error);
  letter-spacing: 0.22em;
}

.write-thread__error-body {
  margin: 0;
  color: var(--calliope-paper);
  font-size: 0.85rem;
  line-height: 1.6;
}
</style>
