<script setup lang="ts">
import { computed, ref } from 'vue'
import { Motion } from 'motion-v'

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
  'delete-session': [sessionId: string]
  'create-folder': [name: string]
  'rename-folder': [folderId: string, name: string]
  'delete-folder': [folderId: string]
}>()

const filter = ref('')
const newFolderName = ref('')
const collapsedFolders = ref<Set<string>>(new Set())

const visibleSessions = computed(() => {
  const needle = filter.value.trim().toLowerCase()
  if (needle.length === 0) return props.sessions
  return props.sessions.filter((session) =>
    (session.title ?? 'Untitled').toLowerCase().includes(needle),
  )
})

const unfiledSessions = computed(() =>
  visibleSessions.value.filter((session) => session.folder_id === null),
)

function sessionsForFolder(folderId: string): SessionSummary[] {
  return visibleSessions.value.filter((session) => session.folder_id === folderId)
}

function createFolder() {
  const name = newFolderName.value.trim()
  if (name.length === 0) return
  emit('create-folder', name)
  newFolderName.value = ''
}

function toggleFolder(folderId: string) {
  const next = new Set(collapsedFolders.value)
  if (next.has(folderId)) {
    next.delete(folderId)
  } else {
    next.add(folderId)
  }
  collapsedFolders.value = next
}

function isCollapsed(folderId: string): boolean {
  return collapsedFolders.value.has(folderId)
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  const now = new Date()
  const sameYear = date.getFullYear() === now.getFullYear()
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    ...(sameYear ? {} : { year: 'numeric' }),
  })
}
</script>

<template>
  <aside class="conversation-drawer calliope-sidebar-grain">
    <header class="drawer-brand">
      <span class="drawer-brand__wordmark calliope-serif">Calliope</span>
      <span class="drawer-brand__sub calliope-eyebrow">Studio</span>
    </header>

    <section class="drawer-workspace">
      <span class="calliope-eyebrow drawer-workspace__label">Workspace</span>
      <span class="drawer-workspace__name calliope-serif">{{ activeWorkspaceName }}</span>
    </section>

    <div class="drawer-actions">
      <v-btn
        block
        class="drawer-actions__new"
        color="primary"
        prepend-icon="mdi-plus"
        @click="emit('new-session')"
      >
        New conversation
      </v-btn>
    </div>

    <div class="drawer-filters">
      <v-text-field
        v-model="filter"
        placeholder="Filter conversations"
        prepend-inner-icon="mdi-magnify"
        class="drawer-filters__input"
      />
      <div class="drawer-filters__folder">
        <v-text-field
          v-model="newFolderName"
          placeholder="New folder"
          class="drawer-filters__input"
          @keyup.enter="createFolder"
        />
        <v-btn
          icon="mdi-folder-plus-outline"
          variant="text"
          density="comfortable"
          size="small"
          color="default"
          aria-label="Create folder"
          @click="createFolder"
        />
      </div>
    </div>

    <nav class="drawer-list" aria-label="Conversations">
      <div v-for="folder in folders" :key="folder.id" class="drawer-folder">
        <div class="drawer-folder__head">
          <button
            type="button"
            class="drawer-folder__toggle"
            :aria-expanded="!isCollapsed(folder.id)"
            @click="toggleFolder(folder.id)"
          >
            <span class="drawer-folder__chevron" :class="{ 'is-open': !isCollapsed(folder.id) }">
              <v-icon size="14" icon="mdi-chevron-right" />
            </span>
            <span class="drawer-folder__name calliope-serif">{{ folder.name }}</span>
            <span class="drawer-folder__count calliope-mono">{{ sessionsForFolder(folder.id).length }}</span>
          </button>
          <button
            type="button"
            class="drawer-folder__delete"
            aria-label="Delete folder"
            @click.stop="emit('delete-folder', folder.id)"
          >
            <v-icon size="14" icon="mdi-close" />
          </button>
        </div>

        <ul v-if="!isCollapsed(folder.id)" class="drawer-sessions">
          <Motion
            v-for="(session, index) in sessionsForFolder(folder.id)"
            :key="session.id"
            tag="li"
            :initial="{ opacity: 0, y: 6 }"
            :animate="{ opacity: 1, y: 0 }"
            :transition="{ duration: 0.22, delay: index * 0.03, ease: [0.16, 1, 0.3, 1] }"
            class="drawer-session-row"
          >
            <button
              type="button"
              class="drawer-session"
              :class="{ 'is-active': session.id === activeSessionId }"
              @click="emit('open-session', session.id)"
            >
              <span class="drawer-session__bar" aria-hidden="true" />
              <span class="drawer-session__title calliope-serif">{{
                session.title ?? 'Untitled'
              }}</span>
              <span class="drawer-session__meta calliope-mono">{{
                formatTimestamp(session.updated_at)
              }}</span>
            </button>
            <button
              type="button"
              class="drawer-session__delete"
              aria-label="Delete conversation"
              @click.stop="emit('delete-session', session.id)"
            >
              <v-icon size="14" icon="mdi-delete-outline" />
            </button>
          </Motion>
          <li v-if="sessionsForFolder(folder.id).length === 0" class="drawer-empty calliope-mono">
            Empty folder
          </li>
        </ul>
      </div>

      <div class="drawer-section">
        <span class="calliope-eyebrow drawer-section__label">Recent</span>
        <ul class="drawer-sessions">
          <Motion
            v-for="(session, index) in unfiledSessions"
            :key="session.id"
            tag="li"
            :initial="{ opacity: 0, y: 6 }"
            :animate="{ opacity: 1, y: 0 }"
            :transition="{ duration: 0.22, delay: index * 0.03, ease: [0.16, 1, 0.3, 1] }"
            class="drawer-session-row"
          >
            <button
              type="button"
              class="drawer-session"
              :class="{ 'is-active': session.id === activeSessionId }"
              @click="emit('open-session', session.id)"
            >
              <span class="drawer-session__bar" aria-hidden="true" />
              <span class="drawer-session__title calliope-serif">{{
                session.title ?? 'Untitled'
              }}</span>
              <span class="drawer-session__meta calliope-mono">{{
                formatTimestamp(session.updated_at)
              }}</span>
            </button>
            <button
              type="button"
              class="drawer-session__delete"
              aria-label="Delete conversation"
              @click.stop="emit('delete-session', session.id)"
            >
              <v-icon size="14" icon="mdi-delete-outline" />
            </button>
          </Motion>
          <li v-if="unfiledSessions.length === 0" class="drawer-empty calliope-mono">
            No conversations yet
          </li>
        </ul>
      </div>
    </nav>
  </aside>
</template>

<style scoped>
.conversation-drawer {
  display: grid;
  grid-template-rows: auto auto auto auto 1fr;
  min-height: 0;
  background: var(--calliope-ink);
  border-right: 1px solid var(--calliope-border-strong);
  /* z-index keeps the grain ::after above scrollable content */
  z-index: 0;
}

.drawer-brand {
  display: flex;
  align-items: baseline;
  gap: 0.55rem;
  padding: var(--calliope-space-lg) var(--calliope-space-md) var(--calliope-space-xs);
  /* Gilt underline echoing the manuscript turn-rule motif */
  border-bottom: 1px solid var(--calliope-border);
  position: relative;
}

/* Gilt accent rule beneath the brand wordmark */
.drawer-brand::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: var(--calliope-space-md);
  right: var(--calliope-space-md);
  height: 1px;
  background: linear-gradient(
    to right,
    transparent 0%,
    var(--calliope-rule) 30%,
    var(--calliope-rule) 70%,
    transparent 100%
  );
  opacity: 0.28;
  pointer-events: none;
}

.drawer-brand__wordmark {
  font-size: 1.5rem;
  font-weight: 380;
  letter-spacing: -0.02em;
  color: var(--calliope-paper);
  font-variation-settings: 'opsz' 100, 'SOFT' 50;
}

.drawer-brand__sub {
  color: var(--calliope-paper-dim);
  font-size: 0.6rem;
  letter-spacing: 0.24em;
}

.drawer-workspace {
  padding: var(--calliope-space-sm) var(--calliope-space-md) var(--calliope-space-sm);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  border-bottom: 1px solid var(--calliope-border);
}

.drawer-workspace__label {
  color: var(--calliope-paper-dim);
}

.drawer-workspace__name {
  font-size: 0.98rem;
  color: var(--calliope-paper);
  letter-spacing: -0.005em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.drawer-actions {
  padding: var(--calliope-space-sm) var(--calliope-space-md) var(--calliope-space-xs);
}

.drawer-actions__new {
  letter-spacing: 0.015em;
}

.drawer-filters {
  padding: 0 var(--calliope-space-md) var(--calliope-space-sm);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.drawer-filters__input :deep(input::placeholder) {
  font-family: var(--calliope-font-mono);
  font-size: 0.78rem;
  letter-spacing: 0.02em;
  color: var(--calliope-paper-dim);
}

.drawer-filters__folder {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 0.35rem;
}

.drawer-list {
  overflow-y: auto;
  padding: var(--calliope-space-xs) var(--calliope-space-xs) var(--calliope-space-xl);
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.drawer-folder {
  display: flex;
  flex-direction: column;
}

.drawer-folder__head {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  border-radius: var(--calliope-radius-md);
  transition: background-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.drawer-folder__head:hover {
  background: var(--calliope-overlay-hover);
}

.drawer-folder__toggle {
  display: grid;
  grid-template-columns: 16px 1fr auto;
  align-items: center;
  gap: 0.55rem;
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: none;
  border-radius: var(--calliope-radius-md);
  color: var(--calliope-paper-muted);
  cursor: pointer;
  text-align: left;
}

.drawer-folder__toggle:hover {
  color: var(--calliope-paper);
}

.drawer-folder__chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--calliope-paper-dim);
  transition: transform var(--calliope-duration-base) var(--calliope-ease-out);
}

.drawer-folder__chevron.is-open {
  transform: rotate(90deg);
}

.drawer-folder__name {
  font-size: 0.85rem;
  letter-spacing: -0.005em;
}

.drawer-folder__count {
  font-size: 0.66rem;
  color: var(--calliope-paper-dim);
  letter-spacing: 0.06em;
}

.drawer-folder__delete {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  margin-right: 0.5rem;
  background: transparent;
  border: none;
  color: var(--calliope-paper-dim);
  border-radius: var(--calliope-radius-sm);
  cursor: pointer;
  opacity: 0;
  transition:
    opacity var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.drawer-folder__head:hover .drawer-folder__delete,
.drawer-folder__delete:focus-visible {
  opacity: 1;
}

.drawer-folder__delete:hover {
  color: var(--calliope-warm-error);
}

.drawer-sessions {
  list-style: none;
  margin: 0;
  padding: 0.1rem 0 0.4rem;
  display: flex;
  flex-direction: column;
}

.drawer-session-row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
}

.drawer-session {
  display: grid;
  grid-template-columns: 3px 1fr auto;
  align-items: baseline;
  gap: 0.65rem;
  width: 100%;
  padding: 0.55rem 0.85rem 0.55rem 0.45rem;
  background: transparent;
  border: none;
  border-radius: var(--calliope-radius-md);
  cursor: pointer;
  text-align: left;
  color: var(--calliope-paper-muted);
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.drawer-session:hover {
  background: var(--calliope-overlay-hover);
  color: var(--calliope-paper);
}

.drawer-session.is-active {
  background: var(--calliope-overlay-active);
  color: var(--calliope-paper);
  /* Warm inner glow on the active row evoking candlelight illumination */
  box-shadow: inset 0 0 0 1px var(--calliope-bronze-veil);
}

.drawer-session__bar {
  width: 2px;
  height: 18px;
  border-radius: 2px;
  background: transparent;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-fast) var(--calliope-ease-out);
}

.drawer-session.is-active .drawer-session__bar {
  background: var(--calliope-bronze);
  /* Gilt glow bloom on the active indicator bar */
  box-shadow: 0 0 6px 1px var(--calliope-bronze-glow);
}

.drawer-session__title {
  font-size: 0.9rem;
  letter-spacing: -0.005em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.drawer-session__meta {
  font-size: 0.66rem;
  color: var(--calliope-paper-dim);
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.drawer-session.is-active .drawer-session__meta {
  color: var(--calliope-paper-muted);
}

.drawer-session__delete {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  margin-right: 0.25rem;
  background: transparent;
  border: none;
  color: var(--calliope-paper-dim);
  border-radius: var(--calliope-radius-sm);
  cursor: pointer;
  opacity: 0;
  transition:
    opacity var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    background-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.drawer-session-row:hover .drawer-session__delete,
.drawer-session__delete:focus-visible {
  opacity: 1;
}

.drawer-session__delete:hover {
  background: var(--calliope-overlay-hover);
  color: var(--calliope-warm-error);
}

.drawer-empty {
  padding: 0.6rem 0.85rem;
  font-size: 0.72rem;
  color: var(--calliope-paper-dim);
  letter-spacing: 0.04em;
}

.drawer-section {
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
}

.drawer-section__label {
  padding: 0.4rem 0.85rem;
  color: var(--calliope-paper-dim);
}
</style>
