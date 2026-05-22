<script setup lang="ts">
import { nextTick, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'

import { useSettingsStore, type SettingsTab } from '../stores/settingsStore'
import ProfilePanel from '@/features/profiles/components/ProfilePanel.vue'
import WorkspacePanel from '@/features/workspaces/components/WorkspacePanel.vue'
import ReindexPanel from '@/features/workspaces/components/ReindexPanel.vue'
import AppearancePanel from './AppearancePanel.vue'

const settings = useSettingsStore()

interface TabDef {
  id: SettingsTab
  label: string
}

const tabs: TabDef[] = [
  { id: 'profiles', label: 'LLM Profiles' },
  { id: 'workspaces', label: 'Workspaces' },
  { id: 'indexing', label: 'Indexing' },
  { id: 'appearance', label: 'Appearance' },
]

const tabRefs = ref<Record<string, HTMLButtonElement | null>>({})
const indicatorLeft = ref(0)
const indicatorWidth = ref(0)

function setTabRef(id: string, el: Element | ComponentPublicInstance | null) {
  tabRefs.value[id] = (el as HTMLButtonElement | null) ?? null
}

async function syncIndicator() {
  await nextTick()
  const el = tabRefs.value[settings.tab]
  if (!el) return
  indicatorLeft.value = el.offsetLeft
  indicatorWidth.value = el.offsetWidth
}

watch(() => settings.tab, syncIndicator)
watch(
  () => settings.open,
  (next) => {
    if (next) {
      syncIndicator()
    }
  },
)
onMounted(syncIndicator)
</script>

<template>
  <v-dialog
    :model-value="settings.open"
    max-width="960"
    transition="scale-transition"
    @update:model-value="settings.open = $event"
  >
    <div class="settings-shell">
      <header class="settings-header">
        <div class="settings-header__meta">
          <span class="calliope-eyebrow settings-header__eyebrow">Studio</span>
          <h2 class="calliope-display settings-header__title">Settings</h2>
        </div>
        <button
          type="button"
          class="settings-header__close"
          aria-label="Close settings"
          @click="settings.close()"
        >
          <v-icon icon="mdi-close" size="18" />
        </button>
      </header>

      <nav class="settings-tabs" aria-label="Settings sections">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :ref="(el) => setTabRef(tab.id, el)"
          type="button"
          class="settings-tab"
          :class="{ 'is-active': settings.tab === tab.id }"
          role="tab"
          :aria-selected="settings.tab === tab.id"
          @click="settings.tab = tab.id"
        >
          {{ tab.label }}
        </button>
        <span
          class="settings-tabs__indicator"
          :style="{
            transform: `translateX(${indicatorLeft}px)`,
            width: `${indicatorWidth}px`,
          }"
        />
      </nav>

      <div class="settings-body">
        <ProfilePanel v-if="settings.tab === 'profiles'" />
        <WorkspacePanel v-else-if="settings.tab === 'workspaces'" />
        <ReindexPanel v-else-if="settings.tab === 'indexing'" />
        <AppearancePanel v-else-if="settings.tab === 'appearance'" />
      </div>
    </div>
  </v-dialog>
</template>

<style scoped>
.settings-shell {
  background: var(--calliope-ink-top);
  border: 1px solid var(--calliope-border-strong);
  border-radius: var(--calliope-radius-lg);
  box-shadow: var(--calliope-shadow-lift);
  display: flex;
  flex-direction: column;
  max-height: 86vh;
  overflow: hidden;
}

.settings-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.5rem 2rem 1.1rem;
  border-bottom: 1px solid var(--calliope-border-strong);
}

.settings-header__meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.settings-header__eyebrow {
  color: var(--calliope-paper-dim);
}

.settings-header__title {
  margin: 0;
  font-size: 1.65rem;
  color: var(--calliope-paper);
  letter-spacing: -0.014em;
}

.settings-header__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: var(--calliope-radius-sm);
  color: var(--calliope-paper-muted);
  cursor: pointer;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.settings-header__close:hover {
  background: var(--calliope-overlay-hover);
  color: var(--calliope-paper);
}

.settings-tabs {
  position: relative;
  display: flex;
  gap: 0.4rem;
  padding: 0 2rem;
  border-bottom: 1px solid var(--calliope-border-strong);
}

.settings-tab {
  position: relative;
  padding: 0.85rem 0.4rem;
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: var(--calliope-font-body);
  font-size: 0.85rem;
  font-weight: 460;
  letter-spacing: -0.005em;
  color: var(--calliope-paper-muted);
  transition: color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.settings-tab + .settings-tab {
  margin-left: 0.8rem;
}

.settings-tab:hover {
  color: var(--calliope-paper);
}

.settings-tab.is-active {
  color: var(--calliope-paper);
}

.settings-tabs__indicator {
  position: absolute;
  bottom: -1px;
  left: 0;
  height: 2px;
  background: var(--calliope-bronze);
  border-radius: 2px;
  transition:
    transform var(--calliope-duration-base) var(--calliope-ease-out),
    width var(--calliope-duration-base) var(--calliope-ease-out);
  will-change: transform, width;
}

.settings-body {
  padding: 1.5rem 2rem 2rem;
  overflow-y: auto;
  background: var(--calliope-ink-top);
}
</style>
