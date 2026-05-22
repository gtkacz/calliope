<script setup lang="ts">
import { onMounted } from 'vue'

import { useWorkspaceStore } from '../stores/workspaceStore'

const store = useWorkspaceStore()

onMounted(() => store.refresh())
</script>

<template>
  <section class="reindex-panel">
    <v-select
      v-model="store.selectedWorkspaceId"
      :items="store.workspaces"
      item-title="name"
      item-value="id"
      label="Workspace"
    />
    <v-btn color="primary" :loading="store.reindexing" :disabled="store.selectedWorkspaceId === null" @click="store.reindexSelectedWorkspace()">
      Reindex
    </v-btn>
    <v-alert v-if="store.reindexResult" type="success" variant="tonal">
      Indexed {{ store.reindexResult.documents_indexed }} documents and {{ store.reindexResult.chunks_indexed }} chunks.
    </v-alert>
    <v-alert v-if="store.errorMessage" type="error" variant="tonal">{{ store.errorMessage }}</v-alert>
  </section>
</template>

<style scoped>
.reindex-panel {
  display: grid;
  max-width: 520px;
  gap: 12px;
}
</style>
