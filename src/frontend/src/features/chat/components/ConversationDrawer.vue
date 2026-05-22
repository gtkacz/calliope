<script setup lang="ts">
import { computed, ref } from 'vue'

import type { ConversationFolder, SessionSummary } from '../types'

const props = defineProps<{
  folders: ConversationFolder[]
  sessions: SessionSummary[]
  activeSessionId: string | null
  activeWorkspaceName: string
}>()

const emit = defineEmits<{
  'new-session': []
  'open-session': [sessionId: string]
  'create-folder': [name: string]
  'rename-folder': [folderId: string, name: string]
  'delete-folder': [folderId: string]
}>()

const filter = ref('')
const newFolderName = ref('')

const visibleSessions = computed(() => {
  const needle = filter.value.trim().toLowerCase()
  if (needle.length === 0) return props.sessions
  return props.sessions.filter((session) => (session.title ?? 'Untitled').toLowerCase().includes(needle))
})

const unfiledSessions = computed(() => visibleSessions.value.filter((session) => session.folder_id === null))

function sessionsForFolder(folderId: string): SessionSummary[] {
  return visibleSessions.value.filter((session) => session.folder_id === folderId)
}

function createFolder() {
  const name = newFolderName.value.trim()
  if (name.length === 0) return
  emit('create-folder', name)
  newFolderName.value = ''
}
</script>

<template>
  <aside class="conversation-drawer">
    <div class="drawer-header">
      <v-btn block color="primary" prepend-icon="mdi-plus" @click="emit('new-session')">
        New conversation
      </v-btn>
      <div class="workspace-name">{{ activeWorkspaceName }}</div>
      <v-text-field v-model="filter" label="Filter conversations" prepend-inner-icon="mdi-magnify" />
      <div class="folder-create">
        <v-text-field v-model="newFolderName" label="Folder name" @keyup.enter="createFolder" />
        <v-btn icon="mdi-folder-plus" variant="text" aria-label="Create folder" @click="createFolder" />
      </div>
    </div>

    <v-list density="compact" nav>
      <v-list-group v-for="folder in folders" :key="folder.id" :value="folder.id">
        <template #activator="{ props: activatorProps }">
          <v-list-item v-bind="activatorProps" prepend-icon="mdi-folder" :title="folder.name">
            <template #append>
              <v-btn icon="mdi-delete-outline" variant="text" size="small" aria-label="Delete folder" @click.stop="emit('delete-folder', folder.id)" />
            </template>
          </v-list-item>
        </template>
        <v-list-item
          v-for="session in sessionsForFolder(folder.id)"
          :key="session.id"
          :active="session.id === activeSessionId"
          :title="session.title ?? 'Untitled'"
          prepend-icon="mdi-message-text-outline"
          @click="emit('open-session', session.id)"
        />
        <v-list-item v-if="sessionsForFolder(folder.id).length === 0" title="Empty folder" class="empty-row" />
      </v-list-group>

      <v-list-subheader>Recent unfiled</v-list-subheader>
      <v-list-item
        v-for="session in unfiledSessions"
        :key="session.id"
        :active="session.id === activeSessionId"
        :title="session.title ?? 'Untitled'"
        prepend-icon="mdi-message-text-outline"
        @click="emit('open-session', session.id)"
      />
      <v-list-item v-if="unfiledSessions.length === 0" title="No unfiled conversations" class="empty-row" />
    </v-list>
  </aside>
</template>

<style scoped>
.conversation-drawer {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
  background: rgb(var(--v-theme-surface));
  border-right: 1px solid rgba(49, 92, 114, 0.14);
}
.drawer-header {
  display: grid;
  gap: 10px;
  padding: 14px;
}
.workspace-name {
  color: rgba(0, 0, 0, 0.64);
  font-size: 0.82rem;
}
.folder-create {
  display: grid;
  grid-template-columns: 1fr 40px;
  gap: 6px;
  align-items: start;
}
.empty-row {
  opacity: 0.62;
}
</style>
