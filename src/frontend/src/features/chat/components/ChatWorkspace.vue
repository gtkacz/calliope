<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { apiBaseUrl } from '@/shared/api/client'
import { useChatStore } from '../stores/chatStore'
import { useProfileStore } from '@/features/profiles/stores/profileStore'
import { useSettingsStore } from '@/features/settings/stores/settingsStore'
import { useWorkspaceStore } from '@/features/workspaces/stores/workspaceStore'
import SettingsDialog from '@/features/settings/components/SettingsDialog.vue'
import ComposerBar from './ComposerBar.vue'
import ConversationDrawer from './ConversationDrawer.vue'
import ConversationTimeline from './ConversationTimeline.vue'

const chat = useChatStore()
const profile = useProfileStore()
const settings = useSettingsStore()
const workspace = useWorkspaceStore()

const startupError = ref(false)
const startupLoading = ref(false)
const apiBaseUrlValue = apiBaseUrl()

const activeWorkspaceName = computed(() => {
  const id = chat.selectedWorkspaceId
  if (id === null) return 'No workspace selected'
  return workspace.workspaces.find((w) => w.id === id)?.name ?? 'No workspace selected'
})

const activeProfileName = computed(() => {
  if (chat.selectedChatProfileId === null) return null
  return profile.chatProfiles.find((p) => p.id === chat.selectedChatProfileId)?.name ?? null
})

const needsWorkspace = computed(
  () => !startupError.value && workspace.workspaces.length === 0,
)
const needsProfile = computed(
  () => !startupError.value && !needsWorkspace.value && profile.chatProfiles.length === 0,
)

function startNewConversation() {
  chat.activeSessionId = null
  chat.messages = []
}

async function loadInitialData() {
  if (startupLoading.value) return
  startupLoading.value = true
  startupError.value = false
  try {
    await Promise.all([workspace.refresh(), profile.refresh(), chat.refreshConversationList()])
  } catch {
    startupError.value = true
    return
  } finally {
    startupLoading.value = false
  }
  if (chat.selectedWorkspaceId === null && workspace.workspaces.length > 0) {
    chat.selectedWorkspaceId = workspace.workspaces[0].id
  }
  if (chat.selectedChatProfileId === null && profile.chatProfiles.length > 0) {
    chat.selectedChatProfileId = profile.chatProfiles[0].id
  }
}

onMounted(loadInitialData)
</script>

<template>
  <div class="chat-shell">
    <ConversationDrawer
      :folders="chat.folders"
      :sessions="chat.sessions"
      :active-session-id="chat.activeSessionId"
      :active-workspace-name="activeWorkspaceName"
      @new-session="startNewConversation"
      @open-session="chat.openSession"
    />

    <section class="chat-main">
      <header class="chat-context">
        <div class="chat-context__meta">
          <span class="calliope-eyebrow">Workspace</span>
          <span class="chat-context__title calliope-serif">{{ activeWorkspaceName }}</span>
        </div>
        <div class="chat-context__actions">
          <span v-if="activeProfileName" class="chat-context__profile calliope-mono">
            <span class="chat-context__profile-dot" aria-hidden="true">●</span>
            {{ activeProfileName }}
          </span>
          <v-btn
            class="chat-context__settings"
            icon="mdi-cog-outline"
            variant="text"
            size="small"
            density="comfortable"
            color="default"
            aria-label="Settings"
            @click="settings.show()"
          />
        </div>
      </header>

      <div class="chat-body">
        <div v-if="startupError" class="chat-fallback">
          <p class="calliope-eyebrow">Connection</p>
          <h1 class="calliope-display-lg chat-fallback__title">
            Calliope can&rsquo;t reach the backend.
          </h1>
          <p class="chat-fallback__detail">
            Tried <span class="calliope-mono">{{ apiBaseUrlValue }}</span> but received no response.
          </p>
          <div class="chat-fallback__action">
            <v-btn
              variant="flat"
              color="primary"
              :loading="startupLoading"
              :disabled="startupLoading"
              @click="loadInitialData"
            >
              Try again
            </v-btn>
          </div>
        </div>

        <ConversationTimeline
          v-else
          :messages="chat.messages"
          :pending="chat.pending"
          :error-message="chat.errorMessage"
        />
      </div>

      <ComposerBar
        v-model:mode="chat.mode"
        v-model:policy="chat.policy"
        v-model:selected-workspace-id="chat.selectedWorkspaceId"
        v-model:selected-chat-profile-id="chat.selectedChatProfileId"
        :workspaces="workspace.workspaces"
        :profiles="profile.chatProfiles"
        :pending="chat.pending"
        :disabled="!chat.canSubmit"
        @submit="chat.submitMessage"
      />

      <footer v-if="needsWorkspace || needsProfile" class="chat-hint">
        <span class="calliope-eyebrow chat-hint__label">Setup</span>
        <span v-if="needsWorkspace">
          Create or select a workspace in
          <button type="button" class="chat-hint__link" @click="settings.show()">Settings</button>
          before submitting turns.
        </span>
        <span v-else-if="needsProfile">
          Create a chat-capable profile in
          <button type="button" class="chat-hint__link" @click="settings.show()">Settings</button>
          before using Chat mode.
        </span>
      </footer>
    </section>

    <SettingsDialog />
  </div>
</template>

<style scoped>
.chat-shell {
  display: grid;
  grid-template-columns: 288px 1fr;
  height: 100vh;
  background: var(--calliope-ink);
}

.chat-main {
  display: grid;
  grid-template-rows: auto 1fr auto auto;
  min-width: 0;
  min-height: 0;
  background: var(--calliope-ink-soft);
}

.chat-context {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.875rem 1.75rem;
  border-bottom: 1px solid var(--calliope-border-strong);
  background: var(--calliope-ink-soft);
}

.chat-context__meta {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

.chat-context__title {
  font-size: 1.0625rem;
  font-weight: 420;
  letter-spacing: -0.005em;
  color: var(--calliope-paper);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-context__actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.chat-context__profile {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.7rem;
  color: var(--calliope-paper-muted);
  padding: 0.25rem 0.7rem;
  background: var(--calliope-overlay-hover);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-pill);
  transition:
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.chat-context__profile:hover {
  color: var(--calliope-paper);
  border-color: var(--calliope-border-strong);
}

.chat-context__profile-dot {
  color: var(--calliope-bronze);
  font-size: 0.5rem;
  line-height: 1;
}

.chat-context__settings :deep(.v-btn__overlay) {
  background: currentColor;
}

.chat-body {
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.chat-fallback {
  margin: auto;
  max-width: 36rem;
  padding: 4rem 2.5rem;
  text-align: left;
}

.chat-fallback__title {
  margin: 0.6rem 0 1.1rem 0;
  color: var(--calliope-paper);
}

.chat-fallback__detail {
  margin: 0 0 1.75rem 0;
  color: var(--calliope-paper-muted);
  font-size: 0.95rem;
  line-height: 1.65;
}

.chat-fallback__action {
  margin-top: 1.25rem;
}

.chat-hint {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding: 0.7rem 1.75rem;
  font-size: 0.8125rem;
  color: var(--calliope-paper-muted);
  border-top: 1px solid var(--calliope-border-strong);
  background: var(--calliope-ink-soft);
}

.chat-hint__label {
  color: var(--calliope-paper-dim);
}

.chat-hint__link {
  background: none;
  border: none;
  padding: 0;
  font: inherit;
  color: var(--calliope-bronze);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
  text-decoration-thickness: 1px;
  text-decoration-color: var(--calliope-bronze-glow);
  transition: text-decoration-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.chat-hint__link:hover {
  text-decoration-color: var(--calliope-bronze);
}
</style>
