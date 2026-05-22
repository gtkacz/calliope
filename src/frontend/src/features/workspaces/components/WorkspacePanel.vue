<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { useWorkspaceStore } from '../stores/workspaceStore'
import type { Workspace } from '../types'

interface WorkspaceForm {
  name: string
  root_path: string
  include_globs: string[]
  exclude_globs: string[]
}

const store = useWorkspaceStore()
const editingId = ref<string | null>(null)
const form = reactive<WorkspaceForm>({
  name: '',
  root_path: '',
  include_globs: ['**/*.md', '**/*.markdown'],
  exclude_globs: ['.git/**', '.venv/**', 'node_modules/**'],
})

onMounted(() => store.refresh())

function edit(workspace: Workspace) {
  editingId.value = workspace.id
  form.name = workspace.name
  form.root_path = workspace.root_path
  form.include_globs = [...workspace.include_globs]
  form.exclude_globs = [...workspace.exclude_globs]
}

async function save() {
  await store.saveWorkspace(
    {
      name: form.name,
      root_path: form.root_path,
      include_globs: form.include_globs,
      exclude_globs: form.exclude_globs,
    },
    editingId.value,
  )
  editingId.value = null
}
</script>

<template>
  <div class="settings-grid">
    <v-list density="compact">
      <v-list-item v-for="workspace in store.workspaces" :key="workspace.id" :title="workspace.name" :subtitle="workspace.root_path">
        <template #append>
          <v-btn icon="mdi-pencil" variant="text" aria-label="Edit workspace" @click="edit(workspace)" />
          <v-btn icon="mdi-delete-outline" variant="text" aria-label="Delete workspace" @click="store.deleteWorkspace(workspace.id)" />
        </template>
      </v-list-item>
    </v-list>
    <form class="settings-form" @submit.prevent="save">
      <v-text-field v-model="form.name" label="Name" />
      <v-text-field
        v-model="form.root_path"
        label="Workspace root"
        hint="Absolute path visible to the backend container (see CALLIOPE_NOTES_DIR in .env)"
        persistent-hint
      />
      <v-combobox
        v-model="form.include_globs"
        label="Include globs"
        multiple
        chips
        closable-chips
        hide-no-data
      />
      <v-combobox
        v-model="form.exclude_globs"
        label="Exclude globs"
        multiple
        chips
        closable-chips
        hide-no-data
      />
      <v-alert v-if="store.errorMessage" type="error" variant="tonal">{{ store.errorMessage }}</v-alert>
      <v-btn type="submit" color="primary">Save workspace</v-btn>
    </form>
  </div>
</template>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: minmax(240px, 340px) 1fr;
  gap: 18px;
}
.settings-form {
  display: grid;
  gap: 10px;
}
</style>
