<script setup lang="ts">
import { computed, onMounted } from 'vue'

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

const activeWorkspaceName = computed(
  () => workspace.selectedWorkspace?.name ?? 'No workspace selected',
)

function startNewConversation() {
  chat.activeSessionId = null
  chat.messages = []
}

onMounted(async () => {
  try {
    await Promise.all([workspace.refresh(), profile.refresh(), chat.refreshConversationList()])
  } catch {
    // Store-level error handling sets errorMessage on each store; no crash.
  }
  if (chat.selectedWorkspaceId === null && workspace.workspaces.length > 0) {
    chat.selectedWorkspaceId = workspace.workspaces[0].id
  }
  if (chat.selectedChatProfileId === null && profile.chatProfiles.length > 0) {
    chat.selectedChatProfileId = profile.chatProfiles[0].id
  }
})
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
      <header class="chat-header">
        <v-btn icon="mdi-cog" variant="text" aria-label="Settings" @click="settings.show()" />
      </header>
      <ConversationTimeline
        :messages="chat.messages"
        :pending="chat.pending"
        :error-message="chat.errorMessage"
      />
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
    </section>
    <SettingsDialog />
  </div>
</template>

<style scoped>
.chat-shell {
  display: grid;
  grid-template-columns: 320px 1fr;
  height: 100vh;
}
.chat-main {
  display: grid;
  grid-template-rows: auto 1fr auto;
  min-height: 0;
}
.chat-header {
  display: flex;
  justify-content: flex-end;
}
</style>
