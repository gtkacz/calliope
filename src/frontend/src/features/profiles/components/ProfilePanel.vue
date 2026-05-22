<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { useProfileStore } from '../stores/profileStore'
import type { Profile, ProfileCapability } from '../types'

const store = useProfileStore()
const editingId = ref<string | null>(null)
const form = reactive({
  name: '',
  kind: 'openai_compatible' as const,
  base_url: '',
  model: '',
  api_key_ref: '',
  capabilities: ['chat'] as ProfileCapability[],
})

const capabilityChoices: ProfileCapability[] = ['chat', 'embeddings', 'rerank', 'streaming']

onMounted(() => store.refresh())

function edit(profile: Profile) {
  editingId.value = profile.id
  form.name = profile.name
  form.kind = profile.kind
  form.base_url = profile.base_url
  form.model = profile.model
  form.api_key_ref = profile.api_key_ref ?? ''
  form.capabilities = [...profile.capabilities]
}

async function save() {
  await store.saveProfile(
    {
      name: form.name,
      kind: form.kind,
      base_url: form.base_url,
      model: form.model,
      api_key_ref: form.api_key_ref.trim() === '' ? null : form.api_key_ref,
      capabilities: form.capabilities,
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
        <span class="calliope-eyebrow">Profiles</span>
        <h3 class="panel-list__title calliope-serif">Models &amp; endpoints</h3>
      </header>
      <ul class="panel-items">
        <li v-for="profile in store.profiles" :key="profile.id" class="panel-item">
          <div class="panel-item__text">
            <span class="panel-item__title calliope-serif">{{ profile.name }}</span>
            <span class="panel-item__sub calliope-mono">{{ profile.model }}</span>
          </div>
          <div class="panel-item__actions">
            <button type="button" class="panel-icon-btn" aria-label="Edit profile" @click="edit(profile)">
              <v-icon icon="mdi-pencil-outline" size="16" />
            </button>
            <button
              type="button"
              class="panel-icon-btn"
              aria-label="Test profile"
              @click="store.testProfile(profile.id)"
            >
              <v-icon icon="mdi-connection" size="16" />
            </button>
            <button
              type="button"
              class="panel-icon-btn panel-icon-btn--danger"
              aria-label="Delete profile"
              @click="store.deleteProfile(profile.id)"
            >
              <v-icon icon="mdi-close" size="16" />
            </button>
          </div>
        </li>
        <li v-if="store.profiles.length === 0" class="panel-empty calliope-mono">
          No profiles yet
        </li>
      </ul>
    </section>

    <form class="panel-form" @submit.prevent="save">
      <header class="panel-form__head">
        <span class="calliope-eyebrow">{{ editingId ? 'Editing' : 'New profile' }}</span>
        <h3 class="panel-form__title calliope-serif">
          {{ editingId ? form.name || 'Profile' : 'Add an endpoint' }}
        </h3>
      </header>

      <div class="panel-field">
        <label class="calliope-eyebrow panel-field__label">Name</label>
        <v-text-field v-model="form.name" placeholder="e.g. Anthropic — Sonnet" />
      </div>
      <div class="panel-field">
        <label class="calliope-eyebrow panel-field__label">Base URL</label>
        <v-text-field v-model="form.base_url" placeholder="https://api.example.com/v1" />
      </div>
      <div class="panel-field">
        <label class="calliope-eyebrow panel-field__label">Model</label>
        <v-text-field v-model="form.model" placeholder="claude-3-5-sonnet" />
      </div>
      <div class="panel-field">
        <label class="calliope-eyebrow panel-field__label">API key (env var)</label>
        <v-text-field v-model="form.api_key_ref" placeholder="ANTHROPIC_API_KEY" />
      </div>
      <div class="panel-field">
        <label class="calliope-eyebrow panel-field__label">Capabilities</label>
        <v-select
          v-model="form.capabilities"
          :items="capabilityChoices"
          multiple
          chips
          closable-chips
        />
      </div>

      <v-alert v-if="store.testResult" type="success" variant="tonal" class="panel-alert">
        Profile test succeeded
      </v-alert>
      <v-alert v-if="store.errorMessage" type="error" variant="tonal" class="panel-alert">
        {{ store.errorMessage }}
      </v-alert>

      <div class="panel-form__actions">
        <v-btn type="submit" color="primary">{{ editingId ? 'Save changes' : 'Add profile' }}</v-btn>
      </div>
    </form>
  </div>
</template>

