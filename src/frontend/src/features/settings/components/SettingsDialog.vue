<script setup lang="ts">
import { useSettingsStore } from '../stores/settingsStore'
import ProfilePanel from '@/features/profiles/components/ProfilePanel.vue'
import WorkspacePanel from '@/features/workspaces/components/WorkspacePanel.vue'
import ReindexPanel from '@/features/workspaces/components/ReindexPanel.vue'

const settings = useSettingsStore()
</script>

<template>
  <v-dialog :model-value="settings.open" max-width="920" @update:model-value="settings.open = $event">
    <v-card>
      <v-card-title class="settings-title">
        Settings
        <v-btn icon="mdi-close" variant="text" aria-label="Close settings" @click="settings.close()" />
      </v-card-title>
      <v-tabs v-model="settings.tab" density="compact">
        <v-tab value="profiles">LLM Profiles</v-tab>
        <v-tab value="workspaces">Workspaces</v-tab>
        <v-tab value="indexing">Indexing</v-tab>
      </v-tabs>
      <v-card-text>
        <v-window v-model="settings.tab">
          <v-window-item value="profiles"><ProfilePanel /></v-window-item>
          <v-window-item value="workspaces"><WorkspacePanel /></v-window-item>
          <v-window-item value="indexing"><ReindexPanel /></v-window-item>
        </v-window>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.settings-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
