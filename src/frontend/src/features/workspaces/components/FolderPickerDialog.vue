<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'

import { ApiError } from '@/shared/api/client'

import { listDirectory } from '../api'
import type { DirectoryEntry, DirectoryListing } from '../types'

interface Props {
  modelValue: boolean
  initialPath?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  select: [path: string]
}>()

const listing = ref<DirectoryListing | null>(null)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)
const manualPath = ref('')
const highlightIndex = ref(-1)
const listEl = ref<HTMLUListElement | null>(null)

interface Crumb {
  label: string
  path: string
}

const breadcrumbs = computed<Crumb[]>(() => {
  if (!listing.value) {
    return []
  }
  const path = listing.value.path
  if (path === '/') {
    return [{ label: '/', path: '/' }]
  }
  const parts = path.split('/').filter(Boolean)
  const crumbs: Crumb[] = [{ label: '/', path: '/' }]
  let acc = ''
  for (const part of parts) {
    acc += `/${part}`
    crumbs.push({ label: part, path: acc })
  }
  return crumbs
})

async function navigate(path?: string): Promise<void> {
  isLoading.value = true
  errorMessage.value = null
  try {
    const result = await listDirectory(path)
    listing.value = result
    manualPath.value = result.path
    highlightIndex.value = -1
    await nextTick()
    listEl.value?.scrollTo({ top: 0 })
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      errorMessage.value = error.message
    } else {
      errorMessage.value = 'Failed to load directory.'
    }
  } finally {
    isLoading.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      navigate(props.initialPath || undefined)
    } else {
      // Reset between openings; preserves a fresh feel.
      listing.value = null
      errorMessage.value = null
      highlightIndex.value = -1
      manualPath.value = ''
    }
  },
)

let debounceTimer: ReturnType<typeof setTimeout> | null = null

function onManualPathInput(value: string): void {
  manualPath.value = value
  if (debounceTimer) {
    clearTimeout(debounceTimer)
  }
  debounceTimer = setTimeout(() => {
    const trimmed = value.trim()
    if (trimmed && trimmed !== listing.value?.path) {
      navigate(trimmed)
    }
  }, 250)
}

onUnmounted(() => {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
  }
})

function selectEntry(entry: DirectoryEntry): void {
  navigate(entry.path)
}

function goUp(): void {
  if (listing.value?.parent) {
    navigate(listing.value.parent)
  }
}

function confirm(): void {
  if (!listing.value) {
    return
  }
  emit('select', listing.value.path)
  emit('update:modelValue', false)
}

function cancel(): void {
  emit('update:modelValue', false)
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }
  const tag = target.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA'
}

function onKeydown(event: KeyboardEvent): void {
  const entries = listing.value?.entries ?? []
  const typing = isTypingTarget(event.target)

  if (event.key === 'ArrowDown' && !typing) {
    event.preventDefault()
    if (entries.length === 0) {
      return
    }
    highlightIndex.value = Math.min(highlightIndex.value + 1, entries.length - 1)
  } else if (event.key === 'ArrowUp' && !typing) {
    event.preventDefault()
    if (entries.length === 0) {
      return
    }
    highlightIndex.value = Math.max(highlightIndex.value - 1, 0)
  } else if (event.key === 'Enter' && !typing) {
    if (highlightIndex.value >= 0 && highlightIndex.value < entries.length) {
      event.preventDefault()
      selectEntry(entries[highlightIndex.value])
    }
  } else if (event.key === 'Backspace' && !typing && listing.value?.parent) {
    event.preventDefault()
    goUp()
  }
}
</script>

<template>
  <v-dialog
    :model-value="modelValue"
    :width="640"
    :max-width="640"
    @update:model-value="(value) => emit('update:modelValue', value)"
  >
    <div class="folder-picker" tabindex="-1" @keydown="onKeydown">
      <header class="folder-picker__head">
        <span class="calliope-eyebrow">Workspace root</span>
        <h2 class="folder-picker__title calliope-serif">Choose a folder</h2>
      </header>

      <nav class="folder-picker__crumbs calliope-mono" aria-label="Path">
        <template v-for="(crumb, i) in breadcrumbs" :key="crumb.path">
          <button
            type="button"
            class="folder-picker__crumb"
            :class="{ 'folder-picker__crumb--current': i === breadcrumbs.length - 1 }"
            @click="navigate(crumb.path)"
          >
            {{ crumb.label }}
          </button>
          <span
            v-if="i < breadcrumbs.length - 1"
            class="folder-picker__crumb-sep"
            aria-hidden="true"
          >/</span>
        </template>
        <span v-if="!listing && !errorMessage" class="folder-picker__crumb-sep">…</span>
      </nav>

      <div class="folder-picker__manual">
        <v-text-field
          :model-value="manualPath"
          density="compact"
          variant="plain"
          hide-details
          placeholder="Type or paste an absolute path"
          prepend-inner-icon="mdi-text-search-variant"
          class="folder-picker__manual-field"
          @update:model-value="onManualPathInput"
        />
        <button
          v-if="listing?.parent"
          type="button"
          class="folder-picker__up"
          :title="`Go to ${listing.parent}`"
          aria-label="Go to parent folder"
          @click="goUp"
        >
          <v-icon icon="mdi-arrow-up" size="16" />
        </button>
      </div>

      <div class="folder-picker__body">
        <div v-if="errorMessage" class="folder-picker__error">
          <v-alert type="error" variant="tonal" density="compact" border="start">
            {{ errorMessage }}
          </v-alert>
        </div>

        <ul v-if="isLoading" class="folder-picker__list folder-picker__list--loading">
          <li v-for="n in 3" :key="n" class="folder-picker__row folder-picker__row--skeleton">
            <span class="folder-picker__skeleton-icon" />
            <span class="folder-picker__skeleton-bar" />
          </li>
        </ul>

        <ul
          v-else-if="listing && listing.entries.length > 0"
          ref="listEl"
          class="folder-picker__list"
          role="listbox"
        >
          <li
            v-for="(entry, idx) in listing.entries"
            :key="entry.path"
            class="folder-picker__row"
            :class="{
              'folder-picker__row--highlight': idx === highlightIndex,
              'folder-picker__row--hidden': entry.is_hidden,
            }"
            :style="{ '--i': Math.min(idx, 12) }"
            role="option"
            :aria-selected="idx === highlightIndex"
            @click="selectEntry(entry)"
            @mouseenter="highlightIndex = idx"
          >
            <v-icon icon="mdi-folder-outline" size="18" class="folder-picker__row-icon" />
            <span class="folder-picker__row-name">{{ entry.name }}</span>
            <v-icon icon="mdi-chevron-right" size="16" class="folder-picker__row-chev" />
          </li>
        </ul>

        <div v-else-if="listing" class="folder-picker__empty calliope-mono">
          No subfolders here
        </div>
      </div>

      <footer class="folder-picker__foot">
        <div class="folder-picker__chosen-wrap">
          <span class="calliope-eyebrow folder-picker__chosen-label">Selected</span>
          <div class="folder-picker__chosen calliope-mono" :title="listing?.path">
            {{ listing?.path ?? '—' }}
          </div>
        </div>
        <div class="folder-picker__actions">
          <button
            type="button"
            class="folder-picker__btn folder-picker__btn--ghost"
            @click="cancel"
          >
            Cancel
          </button>
          <button
            type="button"
            class="folder-picker__btn folder-picker__btn--primary"
            :disabled="!listing"
            @click="confirm"
          >
            Use this folder
          </button>
        </div>
      </footer>
    </div>
  </v-dialog>
</template>

<style scoped>
.folder-picker {
  background: var(--calliope-ink-soft);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-lg);
  box-shadow: var(--calliope-shadow-lift);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  max-height: min(80vh, 720px);
  outline: none;
}

.folder-picker__head {
  padding: 1.35rem 1.5rem 0.95rem;
  border-bottom: 1px solid var(--calliope-border);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.folder-picker__title {
  margin: 0;
  font-size: 1.55rem;
  font-weight: 380;
  color: var(--calliope-paper);
  letter-spacing: -0.014em;
  font-variation-settings: 'opsz' 144, 'SOFT' 55;
}

.folder-picker__crumbs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  padding: 0.85rem 1.5rem 0.35rem;
  font-size: 0.78rem;
  color: var(--calliope-paper-muted);
  min-height: 2rem;
}

.folder-picker__crumb {
  background: none;
  border: none;
  padding: 0.18rem 0.32rem;
  margin: 0;
  color: inherit;
  font: inherit;
  cursor: pointer;
  border-radius: var(--calliope-radius-xs);
  transition: color var(--calliope-duration-fast) var(--calliope-ease-out),
    background-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.folder-picker__crumb:hover,
.folder-picker__crumb:focus-visible {
  color: var(--calliope-bronze);
  background: var(--calliope-bronze-veil);
}

.folder-picker__crumb--current {
  color: var(--calliope-paper);
  font-weight: 500;
}

.folder-picker__crumb-sep {
  color: var(--calliope-paper-faint);
  pointer-events: none;
  padding: 0 0.05rem;
  user-select: none;
}

.folder-picker__manual {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.2rem 1.5rem 0.85rem;
}

.folder-picker__manual-field {
  flex: 1 1 auto;
}

.folder-picker__manual-field :deep(.v-field) {
  background: var(--calliope-ink);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-sm);
  padding: 0 0.5rem;
  transition: border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-fast) var(--calliope-ease-out);
}

.folder-picker__manual-field :deep(.v-field--focused) {
  border-color: var(--calliope-bronze);
  box-shadow: 0 0 0 1px var(--calliope-bronze-glow);
}

.folder-picker__manual-field :deep(.v-field__input),
.folder-picker__manual-field :deep(input) {
  font-family: var(--calliope-font-mono);
  font-size: 0.82rem;
  color: var(--calliope-paper);
  letter-spacing: 0.005em;
}

.folder-picker__manual-field :deep(.v-field__prepend-inner) {
  padding-inline-end: 0.4rem;
}

.folder-picker__manual-field :deep(.v-icon) {
  color: var(--calliope-paper-dim);
  opacity: 0.85;
}

.folder-picker__up {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--calliope-ink);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-sm);
  color: var(--calliope-paper-muted);
  cursor: pointer;
  transition: color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    background-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.folder-picker__up:hover {
  color: var(--calliope-bronze);
  border-color: var(--calliope-bronze);
  background: var(--calliope-bronze-veil);
}

.folder-picker__body {
  flex: 1 1 auto;
  min-height: 240px;
  max-height: 360px;
  overflow-y: auto;
  padding: 0 0.75rem 0.5rem;
  border-top: 1px solid var(--calliope-border);
}

.folder-picker__error {
  padding: 0.75rem 0.75rem 0.25rem;
}

.folder-picker__list {
  list-style: none;
  margin: 0;
  padding: 0.4rem 0;
}

.folder-picker__row {
  display: grid;
  grid-template-columns: 24px 1fr 16px;
  align-items: center;
  gap: 0.7rem;
  padding: 0.55rem 0.75rem;
  border-radius: var(--calliope-radius-sm);
  cursor: pointer;
  color: var(--calliope-paper);
  border-left: 1px solid transparent;
  transition: background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out);
  opacity: 0;
  transform: translateY(4px);
  animation: folder-row-in var(--calliope-duration-base) var(--calliope-ease-out) forwards;
  animation-delay: calc(var(--i, 0) * 28ms);
}

@keyframes folder-row-in {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.folder-picker__row--highlight {
  background: var(--calliope-ink-raised);
  border-left-color: var(--calliope-bronze);
}

.folder-picker__row--hidden {
  color: var(--calliope-paper-muted);
}

.folder-picker__row--hidden .folder-picker__row-icon {
  opacity: 0.65;
}

.folder-picker__row-icon {
  color: var(--calliope-bronze);
}

.folder-picker__row-name {
  font-family: var(--calliope-font-body);
  font-size: 0.92rem;
  letter-spacing: -0.003em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-picker__row-chev {
  color: var(--calliope-paper-faint);
  opacity: 0;
  transform: translateX(-2px);
  transition: opacity var(--calliope-duration-fast) var(--calliope-ease-out),
    transform var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.folder-picker__row:hover .folder-picker__row-chev,
.folder-picker__row--highlight .folder-picker__row-chev {
  opacity: 1;
  transform: translateX(0);
  color: var(--calliope-bronze);
}

.folder-picker__row--skeleton {
  cursor: default;
  animation: none;
  opacity: 1;
  transform: none;
  pointer-events: none;
}

.folder-picker__skeleton-icon {
  display: inline-block;
  width: 18px;
  height: 18px;
  border-radius: var(--calliope-radius-xs);
  background: var(--calliope-border);
  opacity: 0.65;
}

.folder-picker__skeleton-bar {
  height: 12px;
  border-radius: var(--calliope-radius-xs);
  background: linear-gradient(
    90deg,
    var(--calliope-overlay-hover),
    var(--calliope-border),
    var(--calliope-overlay-hover)
  );
  background-size: 200% 100%;
  animation: folder-skeleton-shimmer 1.4s linear infinite;
}

@keyframes folder-skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.folder-picker__empty {
  padding: 2rem 0.75rem;
  text-align: center;
  font-size: 0.78rem;
  color: var(--calliope-paper-dim);
  letter-spacing: 0.04em;
}

.folder-picker__foot {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1rem;
  align-items: center;
  padding: 0.95rem 1.5rem 1.1rem;
  border-top: 1px solid var(--calliope-border);
  background: var(--calliope-ink-soft);
}

.folder-picker__chosen-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
  min-width: 0;
}

.folder-picker__chosen-label {
  color: var(--calliope-paper-dim);
}

.folder-picker__chosen {
  font-size: 0.82rem;
  color: var(--calliope-paper);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  unicode-bidi: plaintext;
  direction: rtl;
  text-align: left;
}

.folder-picker__actions {
  display: inline-flex;
  gap: 0.55rem;
}

.folder-picker__btn {
  font-family: var(--calliope-font-body);
  font-size: 0.83rem;
  font-weight: 500;
  letter-spacing: 0.01em;
  padding: 0.6rem 1.15rem;
  border-radius: var(--calliope-radius-sm);
  cursor: pointer;
  border: 1px solid transparent;
  transition: background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.folder-picker__btn--ghost {
  background: transparent;
  color: var(--calliope-paper-muted);
  border-color: var(--calliope-border);
}

.folder-picker__btn--ghost:hover {
  color: var(--calliope-paper);
  border-color: var(--calliope-border-strong);
  background: var(--calliope-overlay-hover);
}

.folder-picker__btn--primary {
  background: var(--calliope-bronze);
  color: var(--calliope-ink);
}

.folder-picker__btn--primary:hover {
  background: var(--calliope-bronze-deep);
}

.folder-picker__btn--primary:disabled {
  background: var(--calliope-paper-faint);
  color: var(--calliope-paper-dim);
  cursor: not-allowed;
}

@media (max-width: 600px) {
  .folder-picker {
    max-height: 100vh;
    height: 100vh;
    border-radius: 0;
    border: none;
  }

  .folder-picker__body {
    max-height: none;
  }

  .folder-picker__head,
  .folder-picker__crumbs,
  .folder-picker__manual,
  .folder-picker__foot {
    padding-left: 1rem;
    padding-right: 1rem;
  }
}
</style>
