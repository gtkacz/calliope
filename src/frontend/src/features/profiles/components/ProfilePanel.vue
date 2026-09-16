<script setup lang="ts">
import { computed, inject, onMounted, onUnmounted, reactive, ref } from 'vue'

import { draftGuardKey } from '@/features/settings/draftGuard'
import { providerPresets, type ProviderPreset } from '../providerPresets'
import { useProfileStore } from '../stores/profileStore'
import type { Profile, ProfileCapability, ProfileKind } from '../types'

type Mode = 'idle' | 'create' | 'edit'
type Role = 'chat' | 'embeddings' | 'legacy'

const store = useProfileStore()
const draftGuard = inject(draftGuardKey, null)
const mode = ref<Mode>('idle')
const editingId = ref<string | null>(null)
const selectedPresetId = ref<string | null>(null)
const baseline = ref('')
const nameError = ref<string | null>(null)
const saving = ref(false)
const testResult = ref<boolean | null>(null)
const testError = ref<string | null>(null)
const legacyCapabilities = ref<ProfileCapability[]>([])
const loadedRole = ref<Role>('chat')

const form = reactive({
  name: '',
  kind: 'openai_compatible' as ProfileKind,
  base_url: '',
  model: '',
  api_key_ref: '',
  role: 'chat' as Role,
  reranking: false,
  max_tokens: '',
})

const presetOptions = [{ id: null, label: 'Custom' }, ...providerPresets.map((preset) => ({ id: preset.id, label: preset.label }))]
const roleOptions = [
  { value: 'chat', label: 'Chat' },
  { value: 'embeddings', label: 'Embeddings' },
]
const kindOptions: { value: ProfileKind; label: string }[] = [
  { value: 'openai_compatible', label: 'OpenAI-compatible' },
  { value: 'ollama', label: 'Ollama (native API)' },
  { value: 'koboldcpp', label: 'KoboldCpp' },
]

const filteredProfiles = computed(() => {
  const query = search.value.trim().toLocaleLowerCase()
  return query ? store.profiles.filter((profile) => profile.name.toLocaleLowerCase().includes(query)) : store.profiles
})
const search = ref('')
const profileGroups = computed(() => {
  const profiles = filteredProfiles.value
  return [
    { id: 'chat', label: 'Chat models', icon: '$mdi-chat-outline', profiles: profiles.filter((profile) => profile.capabilities.includes('chat')) },
    { id: 'embeddings', label: 'Embedding models', icon: '$mdi-database-outline', profiles: profiles.filter((profile) => profile.capabilities.includes('embeddings')) },
    { id: 'other', label: 'Other', icon: '$mdi-layers-outline', profiles: profiles.filter((profile) => !profile.capabilities.includes('chat') && !profile.capabilities.includes('embeddings')) },
  ].filter((group) => group.profiles.length > 0)
})

function snapshot() {
  return JSON.stringify({ ...form, legacyCapabilities: legacyCapabilities.value })
}
function setBaseline() { baseline.value = snapshot() }
function resetForm() {
  Object.assign(form, { name: '', kind: 'openai_compatible', base_url: '', model: '', api_key_ref: '', role: 'chat', reranking: false, max_tokens: '' })
  legacyCapabilities.value = []
  loadedRole.value = 'chat'
  selectedPresetId.value = null
  nameError.value = null
  testResult.value = null
  testError.value = null
}
function cancel() {
  resetForm()
  mode.value = 'idle'
  editingId.value = null
  setBaseline()
}
function transition(action: () => void) {
  if (snapshot() !== baseline.value) draftGuard?.requestDiscard(action)
  else action()
}
function startNew() {
  transition(() => { resetForm(); mode.value = 'create'; editingId.value = null; setBaseline() })
}
function edit(profile: Profile) {
  transition(() => {
    const primaryRoles = (['chat', 'embeddings'] as const).filter((role) => profile.capabilities.includes(role))
    mode.value = 'edit'
    editingId.value = profile.id
    selectedPresetId.value = null
    Object.assign(form, {
      name: profile.name,
      kind: profile.kind,
      base_url: profile.base_url,
      model: profile.model,
      api_key_ref: profile.api_key_ref ?? '',
      role: primaryRoles.length === 1 ? primaryRoles[0] : 'legacy',
      reranking: profile.capabilities.includes('rerank'),
      max_tokens: profile.max_tokens === null ? '' : String(profile.max_tokens),
    })
    legacyCapabilities.value = [...profile.capabilities]
    loadedRole.value = form.role
    nameError.value = null
    testResult.value = null
    testError.value = null
    setBaseline()
  })
}
function applyPreset(presetId: string | null) {
  if (presetId === null) return
  const preset = providerPresets.find((candidate: ProviderPreset) => candidate.id === presetId)
  if (!preset) return
  form.kind = preset.kind
  form.base_url = preset.base_url
  form.model = preset.model
  form.api_key_ref = preset.api_key_ref ?? ''
  form.role = preset.capabilities.includes('embeddings') && !preset.capabilities.includes('chat') ? 'embeddings' : 'chat'
  form.reranking = preset.capabilities.includes('rerank')
  if (mode.value === 'create' && !form.name.trim()) form.name = preset.label
}
function capabilities(): ProfileCapability[] {
  if (form.role === 'legacy') return [...legacyCapabilities.value]
  const visible: ProfileCapability[] = form.role === 'embeddings' ? ['embeddings'] : form.reranking ? ['chat', 'rerank'] : ['chat']
  // Streaming is no longer editable, but an otherwise ordinary legacy profile
  // should not lose it merely because its name or endpoint changed.
  if (mode.value === 'edit' && form.role === loadedRole.value && legacyCapabilities.value.includes('streaming')) visible.push('streaming')
  return visible
}
async function save() {
  const name = form.name.trim()
  if (!name) { nameError.value = 'Name is required'; return }
  nameError.value = null
  const maxTokens = form.max_tokens.trim()
  const parsedMaxTokens = Number(maxTokens)
  saving.value = true
  try {
    const saved = await store.saveProfile({ name, kind: form.kind, base_url: form.base_url, model: form.model, api_key_ref: form.api_key_ref.trim() || null, capabilities: capabilities(), max_tokens: maxTokens === '' || Number.isNaN(parsedMaxTokens) ? null : parsedMaxTokens }, editingId.value)
    edit(saved)
  } catch {
    // The store owns the request error; preserve this form and its current mode.
  } finally { saving.value = false }
}
async function testActiveProfile() {
  if (!editingId.value) return
  testResult.value = null
  testError.value = null
  try { await store.testProfile(editingId.value); testResult.value = true }
  catch (error) { testError.value = error instanceof Error ? error.message : 'Profile test failed.' }
}

let unregister: (() => void) | undefined
onMounted(() => {
  store.refresh()
  unregister = draftGuard?.register({ isDirty: () => mode.value !== 'idle' && snapshot() !== baseline.value, discard: cancel })
})
onUnmounted(() => unregister?.())
</script>

<template>
  <div class="panel-grid">
    <section class="panel-list">
      <header class="panel-list__head">
        <span class="calliope-eyebrow">Profiles</span>
        <h3 class="panel-list__title calliope-serif">Models &amp; endpoints</h3>
        <v-btn size="small" color="primary" prepend-icon="$mdi-plus" @click="startNew">New profile</v-btn>
      </header>
      <v-text-field v-model="search" density="compact" hide-details placeholder="Filter by name" prepend-inner-icon="$mdi-magnify" class="panel-search" />
      <ul class="panel-items">
        <template v-for="group in profileGroups" :key="group.id">
          <li class="panel-group-label calliope-eyebrow"><v-icon :icon="group.icon" size="14" /> {{ group.label }}</li>
          <li v-for="profile in group.profiles" :key="`${group.id}-${profile.id}`" class="panel-item" :class="{ 'panel-item--active': editingId === profile.id }">
            <button type="button" class="panel-item__select" @click="edit(profile)">
              <v-icon :icon="group.icon" size="16" />
              <span class="panel-item__text"><span class="panel-item__title calliope-serif">{{ profile.name }}</span><span class="panel-item__sub calliope-mono">{{ profile.model }}</span></span>
              <span v-if="profile.capabilities.includes('rerank')" class="profile-marker">Reranking</span>
            </button>
            <div class="panel-item__actions">
              <button type="button" class="panel-icon-btn" aria-label="Test profile" @click="testActiveProfile"><v-icon icon="$mdi-connection" size="16" /></button>
              <button type="button" class="panel-icon-btn panel-icon-btn--danger" aria-label="Delete profile" @click="store.deleteProfile(profile.id)"><v-icon icon="$mdi-close" size="16" /></button>
            </div>
          </li>
        </template>
        <li v-if="store.profiles.length === 0" class="panel-empty calliope-mono">No profiles yet</li>
        <li v-else-if="filteredProfiles.length === 0" class="panel-empty calliope-mono">No matching profiles</li>
      </ul>
    </section>

    <section v-if="mode === 'idle'" class="panel-form panel-neutral">
      <span class="calliope-eyebrow">Profiles</span><h3 class="panel-form__title calliope-serif">Select an item or create new</h3>
      <p>Choose a saved endpoint to edit it, or add a new profile.</p><v-btn color="primary" @click="startNew">New profile</v-btn>
    </section>
    <form v-else class="panel-form" @submit.prevent="save">
      <header class="panel-form__head"><span class="calliope-eyebrow">{{ mode === 'edit' ? 'Editing profile' : 'New profile' }}</span><h3 class="panel-form__title calliope-serif">{{ form.name || 'Profile' }}</h3></header>
      <div class="panel-field"><label class="calliope-eyebrow panel-field__label">Provider</label><v-select v-model="selectedPresetId" :items="presetOptions" item-title="label" item-value="id" placeholder="Custom" @update:model-value="applyPreset" /></div>
      <div class="panel-field"><label class="calliope-eyebrow panel-field__label">Name</label><v-text-field v-model="form.name" :error-messages="nameError ?? undefined" placeholder="e.g. Anthropic — Sonnet" @update:model-value="nameError = null" /></div>
      <div class="panel-field"><label class="calliope-eyebrow panel-field__label">Base URL</label><v-text-field v-model="form.base_url" placeholder="https://api.example.com/v1" /></div>
      <div class="panel-field"><label class="calliope-eyebrow panel-field__label">Connection kind</label><v-select v-model="form.kind" :items="kindOptions" item-title="label" item-value="value" /></div>
      <div class="panel-field"><label class="calliope-eyebrow panel-field__label">Model</label><v-text-field v-model="form.model" placeholder="claude-3-5-sonnet" /></div>
      <div class="panel-field"><label class="calliope-eyebrow panel-field__label">API key (env var)</label><v-text-field v-model="form.api_key_ref" placeholder="ANTHROPIC_API_KEY" /></div>
      <div class="panel-field"><label class="calliope-eyebrow panel-field__label">Role</label><v-select v-model="form.role" :items="roleOptions" item-title="label" item-value="value" :disabled="form.role === 'legacy'" /><span v-if="form.role === 'legacy'" class="panel-field__hint">Multiple roles (legacy). Choose a new role to replace legacy capabilities.</span><v-btn v-if="form.role === 'legacy'" size="x-small" variant="text" @click="form.role = 'chat'">Choose a new role</v-btn></div>
      <div v-if="form.role === 'chat'" class="panel-field"><v-switch v-model="form.reranking" color="primary" label="Enable reranking" hide-details /></div>
      <div class="panel-field"><label class="calliope-eyebrow panel-field__label">Max tokens</label><v-text-field v-model="form.max_tokens" type="number" min="1" placeholder="Default (4096)" /></div>
      <v-alert v-if="testResult" type="success" variant="tonal" class="panel-alert">Profile test succeeded</v-alert><v-alert v-if="testError || store.errorMessage" type="error" variant="tonal" class="panel-alert">{{ testError || store.errorMessage }}</v-alert>
      <div class="panel-form__actions"><v-btn variant="text" @click="transition(cancel)">Cancel</v-btn><v-btn v-if="mode === 'edit'" variant="tonal" :disabled="saving" @click="testActiveProfile">Test profile</v-btn><v-btn type="submit" color="primary" :loading="saving" :disabled="saving || !form.name.trim()">{{ mode === 'edit' ? 'Save changes' : 'Create profile' }}</v-btn></div>
    </form>
  </div>
</template>

<style scoped>
.panel-list__head { align-items: flex-start; }.panel-search { margin-bottom: var(--calliope-space-sm); }.panel-item--active { background: var(--calliope-bronze-veil); border-color: var(--calliope-bronze); }.panel-item__select { display: flex; flex: 1; min-width: 0; align-items: center; gap: var(--calliope-space-xs); border: 0; background: transparent; color: inherit; text-align: left; cursor: pointer; }.panel-item__select .panel-item__text { flex: 1; }.panel-group-label { display: flex; align-items: center; gap: .35rem; padding: var(--calliope-space-sm) var(--calliope-space-sm) var(--calliope-space-2xs); color: var(--calliope-paper-dim); }.profile-marker { color: var(--calliope-bronze); font-size: .68rem; white-space: nowrap; }.panel-neutral { align-content: start; }.panel-neutral p { color: var(--calliope-paper-muted); }
</style>
