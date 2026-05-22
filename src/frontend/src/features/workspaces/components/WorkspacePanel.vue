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
  <div class="panel-grid">
    <section class="panel-list">
      <header class="panel-list__head">
        <span class="calliope-eyebrow">Workspaces</span>
        <h3 class="panel-list__title calliope-serif">Note sources</h3>
      </header>
      <ul class="panel-items">
        <li v-for="workspace in store.workspaces" :key="workspace.id" class="panel-item">
          <div class="panel-item__text">
            <span class="panel-item__title calliope-serif">{{ workspace.name }}</span>
            <span class="panel-item__sub calliope-mono">{{ workspace.root_path }}</span>
          </div>
          <div class="panel-item__actions">
            <button
              type="button"
              class="panel-icon-btn"
              aria-label="Edit workspace"
              @click="edit(workspace)"
            >
              <v-icon icon="mdi-pencil-outline" size="16" />
            </button>
            <button
              type="button"
              class="panel-icon-btn panel-icon-btn--danger"
              aria-label="Delete workspace"
              @click="store.deleteWorkspace(workspace.id)"
            >
              <v-icon icon="mdi-close" size="16" />
            </button>
          </div>
        </li>
        <li v-if="store.workspaces.length === 0" class="panel-empty calliope-mono">
          No workspaces yet
        </li>
      </ul>
    </section>

    <form class="panel-form" @submit.prevent="save">
      <header class="panel-form__head">
        <span class="calliope-eyebrow">{{ editingId ? 'Editing' : 'New workspace' }}</span>
        <h3 class="panel-form__title calliope-serif">
          {{ editingId ? form.name || 'Workspace' : 'Point Calliope at a directory' }}
        </h3>
      </header>

      <div class="panel-field">
        <label class="calliope-eyebrow panel-field__label">Name</label>
        <v-text-field v-model="form.name" placeholder="e.g. Personal notes" />
      </div>

      <div class="panel-field">
        <label class="calliope-eyebrow panel-field__label">Workspace root</label>
        <v-text-field v-model="form.root_path" placeholder="/notes" />
        <span class="panel-field__hint">
          Absolute path visible to the backend container. See
          <span class="calliope-mono">CALLIOPE_NOTES_DIR</span> in
          <span class="calliope-mono">.env</span>.
        </span>
      </div>

      <div class="panel-field">
        <label class="calliope-eyebrow panel-field__label">Include globs</label>
        <v-combobox
          v-model="form.include_globs"
          multiple
          chips
          closable-chips
          hide-no-data
          placeholder="**/*.md"
        />
      </div>

      <div class="panel-field">
        <label class="calliope-eyebrow panel-field__label">Exclude globs</label>
        <v-combobox
          v-model="form.exclude_globs"
          multiple
          chips
          closable-chips
          hide-no-data
          placeholder=".git/**"
        />
      </div>

      <v-alert v-if="store.errorMessage" type="error" variant="tonal" class="panel-alert">
        {{ store.errorMessage }}
      </v-alert>

      <div class="panel-form__actions">
        <v-btn type="submit" color="primary">
          {{ editingId ? 'Save changes' : 'Add workspace' }}
        </v-btn>
      </div>
    </form>
  </div>
</template>
