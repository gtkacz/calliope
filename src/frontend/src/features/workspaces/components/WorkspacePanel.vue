<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { useWorkspaceStore } from '../stores/workspaceStore'
import type { Workspace } from '../types'
import FolderPickerDialog from './FolderPickerDialog.vue'

interface WorkspaceForm {
  name: string
  root_path: string
  include_globs: string[]
  exclude_globs: string[]
  guidelines: string
}

const store = useWorkspaceStore()
const editingId = ref<string | null>(null)
const pickerOpen = ref(false)
const form = reactive<WorkspaceForm>({
  name: '',
  root_path: '',
  include_globs: ['**/*.md', '**/*.markdown'],
  exclude_globs: ['.git/**', '.venv/**', 'node_modules/**'],
  guidelines: '',
})

// Soft ceiling only. At the default retrieval limit, sources already inject
// ~9000 chars of canon into the prompt; keeping guidelines under ~a quarter of
// that leaves room for the grounding the answer must use, and stays safe on the
// small-context local models this project targets. Advisory — a longer style
// bible is still allowed; we only warn.
const GUIDELINES_SOFT_LIMIT_CHARS = 2000

const guidelinesTooLong = computed(
  () => form.guidelines.length > GUIDELINES_SOFT_LIMIT_CHARS,
)

onMounted(() => store.refresh())

function edit(workspace: Workspace) {
  editingId.value = workspace.id
  form.name = workspace.name
  form.root_path = workspace.root_path
  form.include_globs = [...workspace.include_globs]
  form.exclude_globs = [...workspace.exclude_globs]
  form.guidelines = workspace.guidelines ?? ''
}

async function save() {
  await store.saveWorkspace(
    {
      name: form.name,
      root_path: form.root_path,
      include_globs: form.include_globs,
      exclude_globs: form.exclude_globs,
      guidelines: form.guidelines,
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
              <v-icon icon="$mdi-pencil-outline" size="16" />
            </button>
            <button
              type="button"
              class="panel-icon-btn panel-icon-btn--danger"
              aria-label="Delete workspace"
              @click="store.deleteWorkspace(workspace.id)"
            >
              <v-icon icon="$mdi-close" size="16" />
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
        <div class="workspace-root">
          <span
            class="workspace-root__path calliope-mono"
            :class="{ 'workspace-root__path--empty': !form.root_path }"
            :title="form.root_path || 'Choose a folder…'"
          >
            {{ form.root_path || 'Choose a folder…' }}
          </span>
          <button
            type="button"
            class="workspace-root__browse"
            @click="pickerOpen = true"
          >
            <v-icon icon="$mdi-folder-search-outline" size="16" />
            <span>Browse</span>
          </button>
        </div>
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

      <div class="panel-field">
        <label class="calliope-eyebrow panel-field__label">Guidelines</label>
        <v-textarea
          v-model="form.guidelines"
          :rows="4"
          auto-grow
          hide-details
          placeholder="Standing context for every response in this workspace — e.g. “this is a dark fantasy world.”"
        />
        <span class="panel-field__hint">
          Injected into chat, write, and editor prompts for this workspace. Toggle
          per request in the composer.
        </span>
        <v-alert
          v-if="guidelinesTooLong"
          type="warning"
          variant="tonal"
          density="compact"
          class="panel-alert"
        >
          {{ form.guidelines.length }} characters — long guidelines crowd out
          retrieved canon and may weaken grounding on small-context models. You can
          still save.
        </v-alert>
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

    <FolderPickerDialog
      v-model="pickerOpen"
      :initial-path="form.root_path"
      @select="(path) => (form.root_path = path)"
    />
  </div>
</template>

<style scoped>
.workspace-root {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--calliope-space-xs);
  padding: var(--calliope-space-xs) var(--calliope-space-sm);
  background: var(--calliope-ink);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-sm);
  transition: border-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.workspace-root:hover,
.workspace-root:focus-within {
  border-color: var(--calliope-border-strong);
}

.workspace-root__path {
  font-size: 0.82rem;
  color: var(--calliope-paper);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  unicode-bidi: plaintext;
  direction: rtl;
  text-align: left;
}

.workspace-root__path--empty {
  color: var(--calliope-paper-dim);
  direction: ltr;
}

.workspace-root__browse {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.7rem;
  background: transparent;
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-xs);
  color: var(--calliope-paper-muted);
  font: inherit;
  font-size: 0.78rem;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    background-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.workspace-root__browse:hover {
  color: var(--calliope-bronze);
  border-color: var(--calliope-bronze);
  background: var(--calliope-bronze-veil);
}
</style>
