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
  <div class="settings-grid">
    <v-list density="compact">
      <v-list-item v-for="profile in store.profiles" :key="profile.id" :title="profile.name" :subtitle="profile.model">
        <template #append>
          <v-btn icon="mdi-pencil" variant="text" aria-label="Edit profile" @click="edit(profile)" />
          <v-btn icon="mdi-connection" variant="text" aria-label="Test profile" @click="store.testProfile(profile.id)" />
          <v-btn icon="mdi-delete-outline" variant="text" aria-label="Delete profile" @click="store.deleteProfile(profile.id)" />
        </template>
      </v-list-item>
    </v-list>
    <form class="settings-form" @submit.prevent="save">
      <v-text-field v-model="form.name" label="Name" />
      <v-text-field v-model="form.base_url" label="Base URL" />
      <v-text-field v-model="form.model" label="Model" />
      <v-text-field v-model="form.api_key_ref" label="API key env var" />
      <v-select v-model="form.capabilities" :items="['chat', 'embeddings', 'rerank', 'streaming']" label="Capabilities" multiple chips />
      <v-alert v-if="store.testResult" type="success" variant="tonal">Profile test succeeded</v-alert>
      <v-alert v-if="store.errorMessage" type="error" variant="tonal">{{ store.errorMessage }}</v-alert>
      <v-btn type="submit" color="primary">Save profile</v-btn>
    </form>
  </div>
</template>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: minmax(220px, 320px) 1fr;
  gap: 18px;
}
.settings-form {
  display: grid;
  gap: 10px;
}
</style>
