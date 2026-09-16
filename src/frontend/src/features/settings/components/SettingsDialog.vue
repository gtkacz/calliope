<script setup lang="ts">
import { nextTick, onMounted, provide, ref, watch, type ComponentPublicInstance } from 'vue'

import { useSettingsStore, type SettingsTab } from '../stores/settingsStore'
import ProfilePanel from '@/features/profiles/components/ProfilePanel.vue'
import WorkspacePanel from '@/features/workspaces/components/WorkspacePanel.vue'
import ReindexPanel from '@/features/workspaces/components/ReindexPanel.vue'
import AppearancePanel from './AppearancePanel.vue'
import { draftGuardKey, type DraftGuard } from '../draftGuard'

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
const activeDraftGuard = ref<DraftGuard | null>(null)
const discardDialogOpen = ref(false)
const pendingDiscardAction = ref<(() => void) | null>(null)

function registerDraftGuard(guard: DraftGuard) {
  activeDraftGuard.value = guard
  return () => {
    if (activeDraftGuard.value === guard) activeDraftGuard.value = null
  }
}

function requestDiscard(action: () => void) {
  if (!activeDraftGuard.value?.isDirty()) {
    action()
    return
  }
  pendingDiscardAction.value = action
  discardDialogOpen.value = true
}

function confirmDiscard() {
  const action = pendingDiscardAction.value
  pendingDiscardAction.value = null
  discardDialogOpen.value = false
  activeDraftGuard.value?.discard()
  action?.()
}

function cancelDiscard() {
  pendingDiscardAction.value = null
  discardDialogOpen.value = false
}

function changeTab(tab: SettingsTab) {
  if (tab !== settings.tab) requestDiscard(() => { settings.tab = tab })
}

function requestClose() {
  requestDiscard(() => settings.close())
}

function onDialogUpdate(next: boolean) {
  if (next) settings.open = true
  else requestClose()
}

provide(draftGuardKey, { register: registerDraftGuard, requestDiscard })

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
    @update:model-value="onDialogUpdate"
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
          @click="requestClose"
        >
          <v-icon icon="$mdi-close" size="18" />
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
          @click="changeTab(tab.id)"
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

    <v-dialog v-model="discardDialogOpen" max-width="420">
      <section class="discard-dialog" role="alertdialog" aria-labelledby="discard-title">
        <h3 id="discard-title" class="calliope-serif">Discard unsaved changes?</h3>
        <p>Your current draft will be lost.</p>
        <div class="discard-dialog__actions">
          <v-btn variant="text" @click="cancelDiscard">Keep editing</v-btn>
          <v-btn color="primary" @click="confirmDiscard">Discard</v-btn>
        </div>
      </section>
    </v-dialog>
  </v-dialog>
</template>

<style scoped>
.settings-shell {
  background: var(--calliope-ink-raised);
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
  gap: var(--calliope-space-md);
  padding: var(--calliope-space-lg) var(--calliope-space-xl) var(--calliope-space-sm);
  border-bottom: 1px solid var(--calliope-border-strong);
}

.settings-header__meta {
  display: flex;
  flex-direction: column;
  gap: var(--calliope-space-2xs);
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
  padding: 0 var(--calliope-space-xl);
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

@media (prefers-reduced-motion: reduce) {
  .settings-tabs__indicator {
    transition: none;
  }
}

.settings-body {
  padding: var(--calliope-space-lg) var(--calliope-space-xl) var(--calliope-space-2xl);
  overflow-y: auto;
  background: var(--calliope-ink-raised);
}

.discard-dialog {
  padding: var(--calliope-space-lg);
  background: var(--calliope-ink-raised);
  border: 1px solid var(--calliope-border-strong);
  border-radius: var(--calliope-radius-md);
  color: var(--calliope-paper);
}

.discard-dialog h3,
.discard-dialog p { margin: 0; }
.discard-dialog p { margin-top: var(--calliope-space-sm); color: var(--calliope-paper-muted); }
.discard-dialog__actions { display: flex; justify-content: flex-end; gap: var(--calliope-space-xs); margin-top: var(--calliope-space-lg); }

/* Scoped input-well treatment.
 * The plain Vuetify variant reads as a thin underline; on a dense settings form
 * that underline is not enough to delimit fields. Inside the settings body only,
 * wrap each field in a recessed ink-soft well with a stronger underline so the
 * eight-or-so inputs parse as discrete affordances without abandoning the
 * editorial restraint of the rest of the dialog. */
.settings-body :deep(.v-field) {
  background: var(--calliope-ink-soft);
  border-radius: var(--calliope-radius-md);
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-fast) var(--calliope-ease-out);
}

.settings-body :deep(.v-field--variant-plain .v-field__outline::before) {
  border-color: var(--calliope-border-strong);
  opacity: 1;
}

.settings-body :deep(.v-field:hover) {
  background: var(--calliope-ink);
}

.settings-body :deep(.v-field--focused) {
  background: var(--calliope-ink);
  box-shadow: 0 0 0 1px var(--calliope-bronze-glow);
}

.settings-body :deep(.v-field--variant-plain.v-field--focused .v-field__outline::before) {
  border-color: var(--calliope-bronze);
  opacity: 1;
}

.settings-body :deep(.v-field__input) {
  padding-inline: 0.85rem;
  padding-block: 0.55rem;
  min-height: 38px;
}

/* Combobox chips: the dim-on-dim treatment loses contrast when the field is
 * recessed. Lift the chip surface and tighten its border for legibility. */
.settings-body :deep(.v-chip.v-chip--variant-tonal) {
  background: var(--calliope-ink-top);
  color: var(--calliope-paper);
  border: 1px solid var(--calliope-border);
}

.settings-body :deep(.v-chip__close) {
  color: var(--calliope-paper-muted);
  opacity: 1;
}

.settings-body :deep(.v-chip__close:hover) {
  color: var(--calliope-paper);
}
</style>
