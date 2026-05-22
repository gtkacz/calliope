<script setup lang="ts">
import { onMounted } from 'vue'

import { useWorkspaceStore } from '../stores/workspaceStore'

const store = useWorkspaceStore()

onMounted(() => store.refresh())
</script>

<template>
  <section class="reindex-panel">
    <header class="reindex-panel__head">
      <span class="calliope-eyebrow">Indexing</span>
      <h3 class="reindex-panel__title calliope-serif">Re-read a workspace</h3>
      <p class="reindex-panel__intro">
        Walks the workspace, parses new and changed notes, and rebuilds the embedding index so
        Calliope sees your latest writing.
      </p>
    </header>

    <div class="panel-field">
      <label class="calliope-eyebrow panel-field__label">Workspace</label>
      <v-select
        v-model="store.selectedWorkspaceId"
        :items="store.workspaces"
        item-title="name"
        item-value="id"
      />
    </div>

    <div class="reindex-panel__actions">
      <v-btn
        color="primary"
        :loading="store.reindexing"
        :disabled="store.selectedWorkspaceId === null"
        @click="store.reindexSelectedWorkspace()"
      >
        Reindex
      </v-btn>
    </div>

    <v-alert v-if="store.reindexResult" type="success" variant="tonal" class="panel-alert">
      Indexed {{ store.reindexResult.documents_indexed }} documents and
      {{ store.reindexResult.chunks_indexed }} chunks.
    </v-alert>
    <v-alert v-if="store.errorMessage" type="error" variant="tonal" class="panel-alert">
      {{ store.errorMessage }}
    </v-alert>
  </section>
</template>

<style scoped>
.reindex-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 36rem;
}

.reindex-panel__head {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding-bottom: 0.55rem;
  border-bottom: 1px solid var(--calliope-border);
}

.reindex-panel__title {
  margin: 0;
  font-size: 1.1rem;
  color: var(--calliope-paper);
  letter-spacing: -0.008em;
}

.reindex-panel__intro {
  margin: 0;
  color: var(--calliope-paper-muted);
  font-size: 0.88rem;
  line-height: 1.6;
}

.reindex-panel__actions {
  margin-top: 0.4rem;
  display: flex;
}
</style>
