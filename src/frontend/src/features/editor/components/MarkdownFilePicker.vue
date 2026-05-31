<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from "vue";

import { ApiError } from "@/shared/api/client";
import type { DirectoryEntry } from "@/features/workspaces/types";

import { listDir } from "../api";
import type { DirectoryListing } from "../api";

interface Props {
  modelValue: boolean;
  initialPath?: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  select: [path: string];
}>();

const listing = ref<DirectoryListing | null>(null);
const isLoading = ref(false);
const errorMessage = ref<string | null>(null);
const highlightIndex = ref(-1);
const listEl = ref<HTMLUListElement | null>(null);

interface Crumb {
  label: string;
  path: string;
}

const breadcrumbs = computed<Crumb[]>(() => {
  if (!listing.value) {
    return [];
  }
  const path = listing.value.path;
  if (path === "/") {
    return [{ label: "/", path: "/" }];
  }
  const parts = path.split("/").filter(Boolean);
  const crumbs: Crumb[] = [{ label: "/", path: "/" }];
  let acc = "";
  for (const part of parts) {
    acc += `/${part}`;
    crumbs.push({ label: part, path: acc });
  }
  return crumbs;
});

function isMarkdown(name: string): boolean {
  return name.endsWith(".md") || name.endsWith(".markdown");
}

async function navigate(path: string): Promise<void> {
  isLoading.value = true;
  errorMessage.value = null;
  try {
    const result = await listDir(path, true);
    listing.value = result;
    highlightIndex.value = -1;
    await nextTick();
    listEl.value?.scrollTo({ top: 0 });
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Failed to load directory.";
    }
  } finally {
    isLoading.value = false;
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      navigate(props.initialPath ?? "/");
    } else {
      // Reset state between openings for a clean feel.
      listing.value = null;
      errorMessage.value = null;
      highlightIndex.value = -1;
    }
  },
);

function handleEntry(entry: DirectoryEntry): void {
  if (entry.is_dir) {
    navigate(entry.path);
  } else {
    emit("select", entry.path);
    emit("update:modelValue", false);
  }
}

function goUp(): void {
  if (listing.value?.parent) {
    navigate(listing.value.parent);
  }
}

function cancel(): void {
  emit("update:modelValue", false);
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA";
}

const visibleEntries = computed<DirectoryEntry[]>(
  () => listing.value?.entries ?? [],
);

function onKeydown(event: KeyboardEvent): void {
  const entries = visibleEntries.value;
  const typing = isTypingTarget(event.target);

  if (event.key === "ArrowDown" && !typing) {
    event.preventDefault();
    highlightIndex.value = Math.min(
      highlightIndex.value + 1,
      entries.length - 1,
    );
  } else if (event.key === "ArrowUp" && !typing) {
    event.preventDefault();
    highlightIndex.value = Math.max(highlightIndex.value - 1, 0);
  } else if (event.key === "Enter" && !typing) {
    if (highlightIndex.value >= 0 && highlightIndex.value < entries.length) {
      event.preventDefault();
      handleEntry(entries[highlightIndex.value]);
    }
  } else if (event.key === "Backspace" && !typing && listing.value?.parent) {
    event.preventDefault();
    goUp();
  }
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null;

function onManualPathInput(value: string): void {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }
  debounceTimer = setTimeout(() => {
    const trimmed = value.trim();
    if (trimmed && trimmed !== listing.value?.path) {
      navigate(trimmed);
    }
  }, 250);
}

onUnmounted(() => {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }
});
</script>

<template>
  <v-dialog
    :model-value="modelValue"
    :width="640"
    :max-width="640"
    @update:model-value="(value) => emit('update:modelValue', value)"
  >
    <div class="file-picker" tabindex="-1" @keydown="onKeydown">
      <header class="file-picker__head">
        <span class="calliope-eyebrow">Editor</span>
        <h2 class="file-picker__title calliope-serif">Choose a file</h2>
      </header>

      <nav class="file-picker__crumbs calliope-mono" aria-label="Path">
        <template v-for="(crumb, i) in breadcrumbs" :key="crumb.path">
          <button
            type="button"
            class="file-picker__crumb"
            :class="{
              'file-picker__crumb--current': i === breadcrumbs.length - 1,
            }"
            @click="navigate(crumb.path)"
          >
            {{ crumb.label }}
          </button>
          <span
            v-if="i < breadcrumbs.length - 1"
            class="file-picker__crumb-sep"
            aria-hidden="true"
            >/</span
          >
        </template>
        <span v-if="!listing && !errorMessage" class="file-picker__crumb-sep"
          >…</span
        >
      </nav>

      <div class="file-picker__manual">
        <v-text-field
          :model-value="listing?.path ?? ''"
          density="compact"
          variant="plain"
          hide-details
          placeholder="Type or paste an absolute path"
          prepend-inner-icon="mdi-text-search-variant"
          class="file-picker__manual-field"
          @update:model-value="onManualPathInput"
        />
        <button
          v-if="listing?.parent"
          type="button"
          class="file-picker__up"
          :title="`Go to ${listing.parent}`"
          aria-label="Go to parent folder"
          @click="goUp"
        >
          <v-icon icon="mdi-arrow-up" size="16" />
        </button>
      </div>

      <div class="file-picker__body">
        <div v-if="errorMessage" class="file-picker__error">
          <v-alert
            type="error"
            variant="tonal"
            density="compact"
            border="start"
          >
            {{ errorMessage }}
          </v-alert>
        </div>

        <ul
          v-if="isLoading"
          class="file-picker__list file-picker__list--loading"
        >
          <li
            v-for="n in 4"
            :key="n"
            class="file-picker__row file-picker__row--skeleton"
          >
            <span class="file-picker__skeleton-icon" />
            <span class="file-picker__skeleton-bar" />
          </li>
        </ul>

        <ul
          v-else-if="listing && listing.entries.length > 0"
          ref="listEl"
          class="file-picker__list"
          role="listbox"
        >
          <li
            v-for="(entry, idx) in listing.entries"
            :key="entry.path"
            class="file-picker__row"
            :class="{
              'file-picker__row--highlight': idx === highlightIndex,
              'file-picker__row--hidden': entry.is_hidden,
              'file-picker__row--file': !entry.is_dir,
              'file-picker__row--md': !entry.is_dir && isMarkdown(entry.name),
            }"
            :style="{ '--i': Math.min(idx, 12) }"
            role="option"
            :aria-selected="idx === highlightIndex"
            @click="handleEntry(entry)"
            @mouseenter="highlightIndex = idx"
          >
            <v-icon
              :icon="
                entry.is_dir
                  ? 'mdi-folder-outline'
                  : isMarkdown(entry.name)
                    ? 'mdi-language-markdown-outline'
                    : 'mdi-file-outline'
              "
              size="18"
              class="file-picker__row-icon"
            />
            <span class="file-picker__row-name">{{ entry.name }}</span>
            <v-icon
              :icon="
                entry.is_dir ? 'mdi-chevron-right' : 'mdi-arrow-right-thin'
              "
              size="16"
              class="file-picker__row-chev"
            />
          </li>
        </ul>

        <div v-else-if="listing" class="file-picker__empty calliope-mono">
          Empty directory
        </div>
      </div>

      <footer class="file-picker__foot">
        <div class="file-picker__chosen-wrap">
          <span class="calliope-eyebrow file-picker__chosen-label"
            >Location</span
          >
          <div class="file-picker__chosen calliope-mono" :title="listing?.path">
            {{ listing?.path ?? "—" }}
          </div>
        </div>
        <div class="file-picker__actions">
          <button
            type="button"
            class="file-picker__btn file-picker__btn--ghost"
            @click="cancel"
          >
            Cancel
          </button>
        </div>
      </footer>
    </div>
  </v-dialog>
</template>

<style scoped>
.file-picker {
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

.file-picker__head {
  padding: var(--calliope-space-lg) var(--calliope-space-lg) var(--calliope-space-sm);
  border-bottom: 1px solid var(--calliope-border);
  display: flex;
  flex-direction: column;
  gap: var(--calliope-space-2xs);
}

.file-picker__title {
  margin: 0;
  font-size: 1.55rem;
  font-weight: 380;
  color: var(--calliope-paper);
  letter-spacing: -0.014em;
  font-variation-settings:
    "opsz" 144,
    "SOFT" 55;
}

.file-picker__crumbs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  padding: var(--calliope-space-sm) var(--calliope-space-lg) var(--calliope-space-2xs);
  font-size: 0.78rem;
  color: var(--calliope-paper-muted);
  min-height: 2rem;
}

.file-picker__crumb {
  background: none;
  border: none;
  padding: 0.18rem 0.32rem;
  margin: 0;
  color: inherit;
  font: inherit;
  cursor: pointer;
  border-radius: var(--calliope-radius-xs);
  transition:
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    background-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.file-picker__crumb:hover,
.file-picker__crumb:focus-visible {
  color: var(--calliope-bronze);
  background: var(--calliope-bronze-veil);
}

.file-picker__crumb--current {
  color: var(--calliope-paper);
  font-weight: 500;
}

.file-picker__crumb-sep {
  color: var(--calliope-paper-faint);
  pointer-events: none;
  padding: 0 0.05rem;
  user-select: none;
}

.file-picker__manual {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--calliope-space-xs);
  padding: var(--calliope-space-2xs) var(--calliope-space-lg) var(--calliope-space-sm);
}

.file-picker__manual-field {
  flex: 1 1 auto;
}

.file-picker__manual-field :deep(.v-field) {
  background: var(--calliope-ink);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-sm);
  padding: 0 0.5rem;
  transition:
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-fast) var(--calliope-ease-out);
}

.file-picker__manual-field :deep(.v-field--focused) {
  border-color: var(--calliope-bronze);
  box-shadow: 0 0 0 1px var(--calliope-bronze-glow);
}

.file-picker__manual-field :deep(.v-field__input),
.file-picker__manual-field :deep(input) {
  font-family: var(--calliope-font-mono);
  font-size: 0.82rem;
  color: var(--calliope-paper);
  letter-spacing: 0.005em;
}

.file-picker__manual-field :deep(.v-field__prepend-inner) {
  padding-inline-end: 0.4rem;
}

.file-picker__manual-field :deep(.v-icon) {
  color: var(--calliope-paper-dim);
  opacity: 0.85;
}

.file-picker__up {
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
  transition:
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    background-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.file-picker__up:hover {
  color: var(--calliope-bronze);
  border-color: var(--calliope-bronze);
  background: var(--calliope-bronze-veil);
}

.file-picker__body {
  flex: 1 1 auto;
  min-height: 240px;
  max-height: 360px;
  overflow-y: auto;
  padding: 0 0.75rem 0.5rem;
  border-top: 1px solid var(--calliope-border);
}

.file-picker__error {
  padding: 0.75rem 0.75rem 0.25rem;
}

.file-picker__list {
  list-style: none;
  margin: 0;
  padding: 0.4rem 0;
}

.file-picker__row {
  display: grid;
  grid-template-columns: 24px 1fr 16px;
  align-items: center;
  gap: 0.7rem;
  padding: 0.55rem 0.75rem;
  border-radius: var(--calliope-radius-sm);
  cursor: pointer;
  color: var(--calliope-paper);
  border-left: 1px solid transparent;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out);
  opacity: 0;
  transform: translateY(4px);
  animation: file-row-in var(--calliope-duration-base) var(--calliope-ease-out)
    forwards;
  animation-delay: calc(var(--i, 0) * 28ms);
}

@keyframes file-row-in {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.file-picker__row--highlight {
  background: var(--calliope-ink-raised);
  border-left-color: var(--calliope-bronze);
}

.file-picker__row--hidden {
  color: var(--calliope-paper-muted);
}

.file-picker__row--hidden .file-picker__row-icon {
  opacity: 0.65;
}

/* Markdown files get the bronze accent; other files are muted */
.file-picker__row-icon {
  color: var(--calliope-bronze);
}

.file-picker__row--file:not(.file-picker__row--md) .file-picker__row-icon {
  color: var(--calliope-paper-dim);
}

.file-picker__row-name {
  font-family: var(--calliope-font-body);
  font-size: 0.92rem;
  letter-spacing: -0.003em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-picker__row-chev {
  color: var(--calliope-paper-faint);
  opacity: 0;
  transform: translateX(-2px);
  transition:
    opacity var(--calliope-duration-fast) var(--calliope-ease-out),
    transform var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.file-picker__row:hover .file-picker__row-chev,
.file-picker__row--highlight .file-picker__row-chev {
  opacity: 1;
  transform: translateX(0);
  color: var(--calliope-bronze);
}

.file-picker__row--skeleton {
  cursor: default;
  animation: none;
  opacity: 1;
  transform: none;
  pointer-events: none;
}

.file-picker__skeleton-icon {
  display: inline-block;
  width: 18px;
  height: 18px;
  border-radius: var(--calliope-radius-xs);
  background: var(--calliope-border);
  opacity: 0.65;
}

.file-picker__skeleton-bar {
  height: 12px;
  border-radius: var(--calliope-radius-xs);
  background: linear-gradient(
    90deg,
    var(--calliope-overlay-hover),
    var(--calliope-border),
    var(--calliope-overlay-hover)
  );
  background-size: 200% 100%;
  animation: file-skeleton-shimmer 1.4s linear infinite;
}

@keyframes file-skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.file-picker__empty {
  padding: 2rem 0.75rem;
  text-align: center;
  font-size: 0.78rem;
  color: var(--calliope-paper-dim);
  letter-spacing: 0.04em;
}

.file-picker__foot {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--calliope-space-md);
  align-items: center;
  padding: var(--calliope-space-sm) var(--calliope-space-lg) var(--calliope-space-md);
  border-top: 1px solid var(--calliope-border);
  background: var(--calliope-ink-soft);
}

.file-picker__chosen-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
  min-width: 0;
}

.file-picker__chosen-label {
  color: var(--calliope-paper-dim);
}

.file-picker__chosen {
  font-size: 0.82rem;
  color: var(--calliope-paper);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  unicode-bidi: plaintext;
  direction: rtl;
  text-align: left;
}

.file-picker__actions {
  display: inline-flex;
  gap: 0.55rem;
}

.file-picker__btn {
  font-family: var(--calliope-font-body);
  font-size: 0.83rem;
  font-weight: 500;
  letter-spacing: 0.01em;
  padding: 0.6rem 1.15rem;
  border-radius: var(--calliope-radius-sm);
  cursor: pointer;
  border: 1px solid transparent;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.file-picker__btn--ghost {
  background: transparent;
  color: var(--calliope-paper-muted);
  border-color: var(--calliope-border);
}

.file-picker__btn--ghost:hover {
  color: var(--calliope-paper);
  border-color: var(--calliope-border-strong);
  background: var(--calliope-overlay-hover);
}
</style>
