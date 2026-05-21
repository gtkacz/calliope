<script setup lang="ts">
import { computed, ref } from 'vue'

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

const disabledReason = computed(() => {
  if (props.pending) return 'Waiting for response'
  if (props.workspaces.length === 0) return 'Workspace required'
  if (props.mode === 'chat' && props.profiles.length === 0) return 'Chat profile required'
  return null
})

function submit() {
  const value = text.value.trim()
  if (value.length === 0 || props.disabled) return
  emit('submit', value)
  text.value = ''
}
</script>

<template>
  <div class="composer">
    <v-textarea
      v-model="text"
      rows="2"
      auto-grow
      label="Message"
      hide-details
      @keydown.enter.exact.prevent="submit"
    />
    <div class="composer-controls">
      <v-btn-toggle :model-value="mode" mandatory density="compact" @update:model-value="emit('update:mode', $event)">
        <v-btn value="chat">Chat</v-btn>
        <v-btn value="search">Search</v-btn>
      </v-btn-toggle>
      <v-select
        :model-value="policy"
        :items="['strict_canon', 'canon_plus_inference', 'creative_but_consistent']"
        label="Policy"
        hide-details
        @update:model-value="emit('update:policy', $event as CanonPolicy)"
      />
      <v-select
        :model-value="selectedWorkspaceId"
        :items="workspaces"
        item-title="name"
        item-value="id"
        label="Workspace"
        hide-details
        @update:model-value="emit('update:selectedWorkspaceId', $event)"
      />
      <v-select
        :model-value="selectedChatProfileId"
        :disabled="mode === 'search'"
        :items="profiles"
        item-title="name"
        item-value="id"
        label="Model"
        hide-details
        @update:model-value="emit('update:selectedChatProfileId', $event)"
      />
      <v-btn icon="mdi-send" color="primary" :loading="pending" :disabled="disabled || text.trim().length === 0" aria-label="Submit" @click="submit" />
    </div>
    <div v-if="disabledReason" class="disabled-reason">{{ disabledReason }}</div>
  </div>
</template>

<style scoped>
.composer {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-top: 1px solid rgba(49, 92, 114, 0.14);
  background: rgb(var(--v-theme-surface));
}
.composer-controls {
  display: grid;
  grid-template-columns: auto minmax(160px, 220px) minmax(160px, 220px) minmax(160px, 220px) 44px;
  gap: 8px;
  align-items: center;
}
.disabled-reason {
  color: rgba(0, 0, 0, 0.58);
  font-size: 0.82rem;
}
@media (max-width: 900px) {
  .composer-controls {
    grid-template-columns: 1fr;
  }
}
</style>
