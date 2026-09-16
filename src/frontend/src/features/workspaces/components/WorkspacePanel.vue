<script setup lang="ts">
import { computed, inject, onMounted, onUnmounted, reactive, ref, watch } from 'vue'

import { draftGuardKey } from '@/features/settings/draftGuard'
import * as workspaceApi from '../api'
import { useWorkspaceStore } from '../stores/workspaceStore'
import type { GlobPreview, Workspace } from '../types'
import FolderPickerDialog from './FolderPickerDialog.vue'

type Mode = 'idle' | 'create' | 'edit'
interface WorkspaceForm { name: string; root_path: string; include_globs: string[]; exclude_globs: string[]; guidelines: string }
interface PreviewInputs { root_path: string; include_globs: string[]; exclude_globs: string[] }

const store = useWorkspaceStore()
const draftGuard = inject(draftGuardKey, null)
const mode = ref<Mode>('idle')
const editingId = ref<string | null>(null)
const pickerOpen = ref(false)
const search = ref('')
const baseline = ref('')
const nameError = ref<string | null>(null)
const saving = ref(false)
const preview = ref<GlobPreview | null>(null)
const previewError = ref<string | null>(null)
const previewLoading = ref(false)
let previewTimer: ReturnType<typeof setTimeout> | undefined
let queuedPreview: PreviewInputs | null = null
let previewInFlight = false
let previewSequence = 0

const form = reactive<WorkspaceForm>({ name: '', root_path: '', include_globs: ['**/*.md', '**/*.markdown'], exclude_globs: ['.git/**', '.venv/**', 'node_modules/**'], guidelines: '' })
const GUIDELINES_SOFT_LIMIT_CHARS = 2000
const guidelinesTooLong = computed(() => form.guidelines.length > GUIDELINES_SOFT_LIMIT_CHARS)
const filteredWorkspaces = computed(() => {
  const query = search.value.trim().toLocaleLowerCase()
  return query ? store.workspaces.filter((workspace) => workspace.name.toLocaleLowerCase().includes(query)) : store.workspaces
})

function snapshot() { return JSON.stringify(form) }
function setBaseline() { baseline.value = snapshot() }
function resetForm() {
  Object.assign(form, { name: '', root_path: '', include_globs: ['**/*.md', '**/*.markdown'], exclude_globs: ['.git/**', '.venv/**', 'node_modules/**'], guidelines: '' })
  nameError.value = null
  clearPreview()
}
function clearPreview() {
  if (previewTimer) clearTimeout(previewTimer)
  queuedPreview = null
  previewSequence += 1
  preview.value = null
  previewError.value = null
  previewLoading.value = false
}
function cancel() { resetForm(); mode.value = 'idle'; editingId.value = null; setBaseline() }
function transition(action: () => void) { if (snapshot() !== baseline.value) draftGuard?.requestDiscard(action); else action() }
function startNew() { transition(() => { resetForm(); mode.value = 'create'; editingId.value = null; setBaseline() }) }
function edit(workspace: Workspace) {
  transition(() => {
    mode.value = 'edit'; editingId.value = workspace.id
    Object.assign(form, { name: workspace.name, root_path: workspace.root_path, include_globs: [...workspace.include_globs], exclude_globs: [...workspace.exclude_globs], guidelines: workspace.guidelines ?? '' })
    nameError.value = null; setBaseline(); schedulePreview()
  })
}
function currentPreviewInputs(): PreviewInputs { return { root_path: form.root_path.trim(), include_globs: [...form.include_globs], exclude_globs: [...form.exclude_globs] } }
function sameInputs(left: PreviewInputs, right: PreviewInputs) { return JSON.stringify(left) === JSON.stringify(right) }
function schedulePreview() {
  if (mode.value === 'idle' || !form.root_path.trim()) { clearPreview(); return }
  if (previewTimer) clearTimeout(previewTimer)
  previewTimer = setTimeout(() => queuePreview(currentPreviewInputs()), 400)
}
function queuePreview(inputs: PreviewInputs) {
  queuedPreview = inputs
  if (!previewInFlight) void runPreview()
}
async function runPreview() {
  const inputs = queuedPreview
  if (!inputs) return
  queuedPreview = null
  previewInFlight = true
  previewLoading.value = true
  previewError.value = null
  const sequence = ++previewSequence
  try {
    const result = await workspaceApi.previewWorkspaceGlobs(inputs)
    if (sequence === previewSequence && !queuedPreview && sameInputs(inputs, currentPreviewInputs())) preview.value = result
  } catch (error) {
    if (sequence === previewSequence && !queuedPreview && sameInputs(inputs, currentPreviewInputs())) {
      preview.value = null
      previewError.value = error instanceof Error ? error.message : 'Could not preview these globs.'
    }
  } finally {
    previewInFlight = false
    if (queuedPreview) void runPreview()
    else if (sequence === previewSequence) previewLoading.value = false
  }
}
async function save() {
  const name = form.name.trim()
  if (!name) { nameError.value = 'Name is required'; return }
  nameError.value = null; saving.value = true
  try {
    const saved = await store.saveWorkspace({ name, root_path: form.root_path, include_globs: form.include_globs, exclude_globs: form.exclude_globs, guidelines: form.guidelines }, editingId.value)
    edit(saved)
  } catch { /* preserve active draft */ } finally { saving.value = false }
}

watch(() => [form.root_path, JSON.stringify(form.include_globs), JSON.stringify(form.exclude_globs), mode.value], schedulePreview)
let unregister: (() => void) | undefined
onMounted(() => { store.refresh(); unregister = draftGuard?.register({ isDirty: () => mode.value !== 'idle' && snapshot() !== baseline.value, discard: cancel }) })
onUnmounted(() => { unregister?.(); if (previewTimer) clearTimeout(previewTimer) })
</script>

<template>
  <div class="panel-grid">
    <section class="panel-list"><header class="panel-list__head"><span class="calliope-eyebrow">Workspaces</span><h3 class="panel-list__title calliope-serif">Note sources</h3><v-btn size="small" color="primary" prepend-icon="$mdi-plus" @click="startNew">New workspace</v-btn></header>
      <v-text-field v-model="search" density="compact" hide-details placeholder="Filter by name" prepend-inner-icon="$mdi-magnify" class="panel-search" />
      <ul class="panel-items"><li v-for="workspace in filteredWorkspaces" :key="workspace.id" class="panel-item" :class="{ 'panel-item--active': editingId === workspace.id }"><button type="button" class="panel-item__select" @click="edit(workspace)"><span class="panel-item__text"><span class="panel-item__title calliope-serif">{{ workspace.name }}</span><span class="panel-item__sub calliope-mono">{{ workspace.root_path }}</span></span></button><div class="panel-item__actions"><button type="button" class="panel-icon-btn panel-icon-btn--danger" aria-label="Delete workspace" @click="store.deleteWorkspace(workspace.id)"><v-icon icon="$mdi-close" size="16" /></button></div></li><li v-if="store.workspaces.length === 0" class="panel-empty calliope-mono">No workspaces yet</li><li v-else-if="filteredWorkspaces.length === 0" class="panel-empty calliope-mono">No matching workspaces</li></ul>
    </section>
    <section v-if="mode === 'idle'" class="panel-form panel-neutral"><span class="calliope-eyebrow">Workspaces</span><h3 class="panel-form__title calliope-serif">Select an item or create new</h3><p>Choose a saved workspace to edit it, or point Calliope at a new directory.</p><v-btn color="primary" @click="startNew">New workspace</v-btn></section>
    <form v-else class="panel-form" @submit.prevent="save"><header class="panel-form__head"><span class="calliope-eyebrow">{{ mode === 'edit' ? 'Editing workspace' : 'New workspace' }}</span><h3 class="panel-form__title calliope-serif">{{ form.name || 'Workspace' }}</h3></header>
      <div class="panel-field"><label class="calliope-eyebrow panel-field__label">Name</label><v-text-field v-model="form.name" :error-messages="nameError ?? undefined" placeholder="e.g. Personal notes" @update:model-value="nameError = null" /></div>
      <div class="panel-field"><label class="calliope-eyebrow panel-field__label">Workspace root</label><div class="workspace-root"><span class="workspace-root__path calliope-mono" :class="{ 'workspace-root__path--empty': !form.root_path }" :title="form.root_path || 'Choose a folder…'">{{ form.root_path || 'Choose a folder…' }}</span><button type="button" class="workspace-root__browse" @click="pickerOpen = true"><v-icon icon="$mdi-folder-search-outline" size="16" /><span>Browse</span></button></div></div>
      <div class="panel-field"><label class="calliope-eyebrow panel-field__label">Include globs</label><v-combobox v-model="form.include_globs" multiple chips closable-chips hide-no-data placeholder="**/*.md" /></div>
      <div class="panel-field"><label class="calliope-eyebrow panel-field__label">Exclude globs</label><v-combobox v-model="form.exclude_globs" multiple chips closable-chips hide-no-data placeholder=".git/**" /></div>
      <section class="glob-preview" aria-live="polite"><span class="calliope-eyebrow">Live preview</span><p v-if="previewLoading">Checking files…</p><p v-else-if="previewError">{{ previewError }}</p><template v-else-if="preview"><p>{{ preview.truncated ? 'At least' : '' }} {{ preview.included.count }} included · {{ preview.truncated ? 'at least' : '' }} {{ preview.ignored.count }} ignored <span v-if="preview.truncated">(scan limit reached)</span></p><div v-if="preview.included.count + preview.ignored.count === 0">No files found.</div><div class="glob-preview__samples"><div><strong>Included</strong><code v-for="path in preview.included.paths" :key="`included-${path}`">{{ path }}</code></div><div><strong>Ignored</strong><code v-for="path in preview.ignored.paths" :key="`ignored-${path}`">{{ path }}</code></div></div></template><p v-else>Choose a root to preview matching files.</p></section>
      <div class="panel-field"><label class="calliope-eyebrow panel-field__label">Guidelines</label><v-textarea v-model="form.guidelines" :rows="4" auto-grow hide-details placeholder="Standing context for every response in this workspace" /><span class="panel-field__hint">Injected into chat, write, and editor prompts for this workspace.</span><v-alert v-if="guidelinesTooLong" type="warning" variant="tonal" density="compact" class="panel-alert">{{ form.guidelines.length }} characters — long guidelines crowd out retrieved canon.</v-alert></div>
      <v-alert v-if="store.errorMessage" type="error" variant="tonal" class="panel-alert">{{ store.errorMessage }}</v-alert><div class="panel-form__actions"><v-btn variant="text" @click="transition(cancel)">Cancel</v-btn><v-btn type="submit" color="primary" :loading="saving" :disabled="saving || !form.name.trim()">{{ mode === 'edit' ? 'Save changes' : 'Create workspace' }}</v-btn></div>
    </form>
    <FolderPickerDialog v-model="pickerOpen" :initial-path="form.root_path" @select="(path) => (form.root_path = path)" />
  </div>
</template>

<style scoped>
.panel-list__head { align-items: flex-start; }.panel-search { margin-bottom: var(--calliope-space-sm); }.panel-item--active { background: var(--calliope-bronze-veil); border-color: var(--calliope-bronze); }.panel-item__select { display: flex; flex: 1; min-width: 0; border: 0; background: transparent; color: inherit; text-align: left; cursor: pointer; }.panel-item__select .panel-item__text { flex: 1; }.panel-neutral { align-content: start; }.panel-neutral p { color: var(--calliope-paper-muted); }.workspace-root { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; gap:var(--calliope-space-xs); padding:var(--calliope-space-xs) var(--calliope-space-sm); background:var(--calliope-ink); border:1px solid var(--calliope-border); border-radius:var(--calliope-radius-sm); }.workspace-root__path { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--calliope-paper); direction:rtl; }.workspace-root__path--empty { color:var(--calliope-paper-dim); direction:ltr; }.workspace-root__browse { display:inline-flex; align-items:center; gap:.35rem; border:1px solid var(--calliope-border); border-radius:var(--calliope-radius-xs); padding:.35rem .7rem; background:transparent; color:var(--calliope-paper-muted); cursor:pointer; }.glob-preview { padding:var(--calliope-space-sm); background:var(--calliope-ink-soft); border:1px solid var(--calliope-border); border-radius:var(--calliope-radius-sm); }.glob-preview p { margin:.35rem 0; color:var(--calliope-paper-muted); }.glob-preview__samples { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:var(--calliope-space-sm); max-height:10rem; overflow:auto; }.glob-preview__samples div { display:flex; flex-direction:column; min-width:0; }.glob-preview code { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--calliope-paper-muted); font-size:.72rem; }
</style>
