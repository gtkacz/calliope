<script setup lang="ts">
import type { MessageRead, SourceReference } from '../types'

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
  <div class="timeline">
    <div v-if="messages.length === 0" class="empty-thread">Start a conversation or run a search.</div>
    <article v-for="message in messages" :key="message.id" class="message" :class="`message-${message.role}`">
      <div class="message-role">{{ message.role === 'search' ? 'Search' : message.role }}</div>
      <p class="message-content">{{ message.content }}</p>
      <div v-if="sourcesFor(message).length > 0" class="sources">
        <v-card v-for="source in sourcesFor(message)" :key="source.chunk_id" class="source-card" variant="outlined">
          <v-card-title>{{ source.path }}</v-card-title>
          <v-card-subtitle>{{ source.heading }}</v-card-subtitle>
          <v-card-text>{{ source.excerpt }}</v-card-text>
        </v-card>
      </div>
    </article>
    <v-progress-linear v-if="pending" indeterminate color="primary" />
    <v-alert v-if="errorMessage" type="error" variant="tonal">{{ errorMessage }}</v-alert>
  </div>
</template>

<style scoped>
.timeline {
  display: grid;
  gap: 14px;
  padding: 24px;
  overflow: auto;
}
.empty-thread {
  align-self: center;
  color: rgba(0, 0, 0, 0.58);
  text-align: center;
}
.message {
  max-width: 880px;
  padding: 14px;
  border: 1px solid rgba(49, 92, 114, 0.14);
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
}
.message-user {
  justify-self: end;
  background: rgba(49, 92, 114, 0.08);
}
.message-role {
  margin-bottom: 6px;
  color: rgba(0, 0, 0, 0.58);
  font-size: 0.78rem;
  text-transform: capitalize;
}
.message-content {
  margin: 0;
  white-space: pre-wrap;
}
.sources {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}
.source-card :deep(.v-card-title) {
  font-size: 0.9rem;
}
</style>
