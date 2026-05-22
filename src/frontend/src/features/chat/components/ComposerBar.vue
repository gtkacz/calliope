<script setup lang="ts">
import { computed, ref } from 'vue'
import { Motion } from 'motion-v'

import type { CanonPolicy, ComposerMode } from '../types'
import type { Profile } from '@/features/profiles/types'
import type { Workspace } from '@/features/workspaces/types'

const props = defineProps<{
  mode: ComposerMode
  policy: CanonPolicy
  selectedWorkspaceId: string | null
  selectedChatProfileId: string | null
  workspaces: Workspace[]
  profiles: Profile[]
  pending: boolean
  disabled: boolean
}>()

const emit = defineEmits<{
  'update:mode': [value: ComposerMode]
  'update:policy': [value: CanonPolicy]
  'update:selectedWorkspaceId': [value: string | null]
  'update:selectedChatProfileId': [value: string | null]
  submit: [value: string]
}>()

const text = ref('')
const focused = ref(false)

const policyItems = [
  { value: 'strict_canon', title: 'Strict canon' },
  { value: 'canon_plus_inference', title: 'Canon + inference' },
  { value: 'creative_but_consistent', title: 'Creative, consistent' },
]

const disabledReason = computed(() => {
  if (props.pending) return 'Waiting for response'
  if (props.workspaces.length === 0) return 'Workspace required'
  if (props.mode === 'chat' && props.profiles.length === 0) return 'Chat profile required'
  return null
})

const canSubmit = computed(() => !props.disabled && text.value.trim().length > 0)

function submit() {
  const value = text.value.trim()
  if (value.length === 0 || props.disabled) return
  emit('submit', value)
  text.value = ''
}

function setMode(next: ComposerMode) {
  if (next === props.mode) return
  emit('update:mode', next)
}
</script>

<template>
  <div class="composer-wrap">
    <div class="composer" :class="{ 'is-focused': focused }">
      <v-textarea
        v-model="text"
        rows="1"
        auto-grow
        variant="plain"
        density="comfortable"
        hide-details
        placeholder="Ask Calliope, or search your notes…"
        class="composer__input"
        @focus="focused = true"
        @blur="focused = false"
        @keydown.enter.exact.prevent="submit"
      />

      <div class="composer__controls">
        <div class="composer__segmented" role="tablist" aria-label="Composer mode">
          <button
            type="button"
            class="composer__segment"
            :class="{ 'is-active': mode === 'chat' }"
            role="tab"
            :aria-selected="mode === 'chat'"
            @click="setMode('chat')"
          >
            Chat
          </button>
          <button
            type="button"
            class="composer__segment"
            :class="{ 'is-active': mode === 'search' }"
            role="tab"
            :aria-selected="mode === 'search'"
            @click="setMode('search')"
          >
            Search
          </button>
        </div>

        <div class="composer__pills">
          <v-select
            :model-value="policy"
            :items="policyItems"
            item-title="title"
            item-value="value"
            variant="plain"
            density="compact"
            hide-details
            class="composer__pill"
            menu-icon="mdi-chevron-down"
            aria-label="Canon policy"
            @update:model-value="emit('update:policy', $event as CanonPolicy)"
          />
          <v-select
            :model-value="selectedWorkspaceId"
            :items="workspaces"
            item-title="name"
            item-value="id"
            variant="plain"
            density="compact"
            hide-details
            placeholder="Workspace"
            class="composer__pill"
            menu-icon="mdi-chevron-down"
            aria-label="Workspace"
            @update:model-value="emit('update:selectedWorkspaceId', $event)"
          />
          <v-select
            :model-value="selectedChatProfileId"
            :disabled="mode === 'search'"
            :items="profiles"
            item-title="name"
            item-value="id"
            variant="plain"
            density="compact"
            hide-details
            placeholder="Model"
            class="composer__pill"
            menu-icon="mdi-chevron-down"
            aria-label="Chat profile"
            @update:model-value="emit('update:selectedChatProfileId', $event)"
          />
        </div>

        <Motion
          tag="div"
          class="composer__send-wrap"
          :while-hover="canSubmit ? { scale: 1.05 } : undefined"
          :while-press="canSubmit ? { scale: 0.94 } : undefined"
          :transition="{ type: 'spring', stiffness: 380, damping: 22 }"
        >
          <button
            type="button"
            class="composer__send"
            :class="{ 'is-active': canSubmit, 'is-pending': pending }"
            :disabled="!canSubmit"
            aria-label="Submit"
            @click="submit"
          >
            <v-icon v-if="!pending" icon="mdi-arrow-up" size="20" />
            <span v-else class="composer__send-spinner" aria-hidden="true" />
          </button>
        </Motion>
      </div>
    </div>

    <p v-if="disabledReason" class="composer__hint calliope-mono">
      {{ disabledReason }}
    </p>
  </div>
</template>

<style scoped>
.composer-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding: 0.85rem 1.75rem 1.1rem;
  background: var(--calliope-ink-soft);
  border-top: 1px solid var(--calliope-border-strong);
}

.composer {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  padding: 0.85rem 1rem 0.75rem 1.15rem;
  background: var(--calliope-ink-raised);
  border: 1px solid var(--calliope-border-strong);
  border-radius: var(--calliope-radius-xl);
  box-shadow: var(--calliope-shadow-rest);
  transition:
    border-color var(--calliope-duration-base) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-base) var(--calliope-ease-out);
}

.composer.is-focused {
  border-color: var(--calliope-bronze);
  box-shadow:
    var(--calliope-shadow-rest),
    0 0 0 4px var(--calliope-bronze-veil);
}

.composer__input :deep(textarea) {
  font-family: var(--calliope-font-body);
  font-size: 0.97rem;
  line-height: 1.6;
  color: var(--calliope-paper);
  padding-top: 0.35rem;
}

.composer__input :deep(textarea::placeholder) {
  color: var(--calliope-paper-dim);
}

.composer__input :deep(.v-field__outline) {
  display: none;
}

.composer__controls {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.65rem;
}

.composer__segmented {
  display: inline-flex;
  padding: 0.15rem;
  background: var(--calliope-overlay-hover);
  border-radius: var(--calliope-radius-pill);
  border: 1px solid var(--calliope-border);
}

.composer__segment {
  padding: 0.32rem 0.85rem;
  background: transparent;
  border: none;
  border-radius: var(--calliope-radius-pill);
  cursor: pointer;
  font-family: var(--calliope-font-body);
  font-size: 0.78rem;
  font-weight: 460;
  letter-spacing: 0.005em;
  color: var(--calliope-paper-muted);
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.composer__segment:hover {
  color: var(--calliope-paper);
}

.composer__segment.is-active {
  background: var(--calliope-ink-top);
  color: var(--calliope-paper);
}

.composer__pills {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  justify-content: flex-end;
  min-width: 0;
}

.composer__pill {
  min-width: 0;
  max-width: 9.5rem;
}

.composer__pill :deep(.v-field) {
  padding: 0 0.6rem 0 0.85rem;
  background: var(--calliope-overlay-hover);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-pill);
  min-height: 28px;
  transition: border-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.composer__pill :deep(.v-field:hover),
.composer__pill :deep(.v-field--focused) {
  border-color: var(--calliope-border-strong);
}

.composer__pill :deep(.v-field__outline) {
  display: none;
}

.composer__pill :deep(.v-field__input) {
  padding: 0;
  min-height: 28px;
  font-family: var(--calliope-font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.02em;
  color: var(--calliope-paper);
}

.composer__pill :deep(.v-field__append-inner) {
  padding-top: 0;
  align-self: center;
}

.composer__pill :deep(.v-field__append-inner .v-icon) {
  opacity: 0.6;
  font-size: 1rem;
}

.composer__send-wrap {
  display: inline-flex;
}

.composer__send {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--calliope-ink-top);
  color: var(--calliope-paper-muted);
  border: 1px solid var(--calliope-border-strong);
  border-radius: 50%;
  cursor: pointer;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.composer__send.is-active {
  background: var(--calliope-bronze);
  color: var(--calliope-ink);
  border-color: var(--calliope-bronze);
}

.composer__send.is-active:hover {
  background: var(--calliope-bronze-deep);
}

.composer__send:disabled {
  cursor: not-allowed;
}

.composer__send-spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--calliope-paper-muted);
  border-top-color: transparent;
  animation: calliope-spin 720ms linear infinite;
}

.composer__send.is-active.is-pending .composer__send-spinner {
  border-color: var(--calliope-ink);
  border-top-color: transparent;
}

@keyframes calliope-spin {
  to {
    transform: rotate(360deg);
  }
}

.composer__hint {
  margin: 0;
  padding-left: 0.25rem;
  color: var(--calliope-paper-dim);
  font-size: 0.7rem;
  letter-spacing: 0.06em;
}

@media (max-width: 900px) {
  .composer__controls {
    grid-template-columns: 1fr auto;
    grid-template-rows: auto auto;
    gap: 0.5rem;
  }

  .composer__segmented {
    grid-row: 1;
  }

  .composer__pills {
    grid-column: 1 / -1;
    grid-row: 2;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .composer__send-wrap {
    grid-row: 1;
    grid-column: 2;
    justify-self: end;
  }
}
</style>
