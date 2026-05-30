<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { DocumentSummary } from "@/features/documents/types";

const props = defineProps<{
  documents: DocumentSummary[];
  query: string;
}>();

const emit = defineEmits<{
  select: [doc: DocumentSummary];
}>();

const highlightIndex = ref(0);

const filtered = computed(() => {
  const q = props.query.toLowerCase();
  if (q.length === 0) {
    return props.documents.slice(0, 20);
  }
  return props.documents.filter(
    (d) =>
      d.title.toLowerCase().includes(q) || d.path.toLowerCase().includes(q),
  );
});

// Reset highlight when the filtered list changes
watch(
  () => filtered.value.length,
  () => {
    highlightIndex.value = 0;
  },
);

function selectHighlighted() {
  const doc = filtered.value[highlightIndex.value];
  if (doc !== undefined) {
    emit("select", doc);
  }
}

function moveHighlight(delta: number) {
  const len = filtered.value.length;
  if (len === 0) return;
  highlightIndex.value = (highlightIndex.value + delta + len) % len;
}

function filename(path: string): string {
  return path.split("/").at(-1) ?? path;
}

defineExpose({ selectHighlighted, moveHighlight });
</script>

<template>
  <div
    v-if="filtered.length > 0"
    class="mention-menu"
    role="listbox"
    aria-label="Document mentions"
  >
    <button
      v-for="(doc, index) in filtered"
      :key="doc.id"
      type="button"
      role="option"
      class="mention-menu__item calliope-mono"
      :class="{ 'is-highlighted': index === highlightIndex }"
      :aria-selected="index === highlightIndex"
      @mouseenter="highlightIndex = index"
      @mousedown.prevent="emit('select', doc)"
    >
      <span class="mention-menu__title">{{ doc.title }}</span>
      <span class="mention-menu__path">{{ filename(doc.path) }}</span>
    </button>
  </div>
</template>

<style scoped>
.mention-menu {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  margin-bottom: 0.4rem;
  background: var(--calliope-ink-raised);
  border: 1px solid var(--calliope-border-strong);
  border-radius: var(--calliope-radius-xl);
  box-shadow: var(--calliope-shadow-rest);
  max-height: 14rem;
  overflow-y: auto;
  z-index: 100;
  padding: 0.3rem;
}

.mention-menu__item {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  width: 100%;
  padding: 0.45rem 0.75rem;
  background: transparent;
  border: none;
  border-radius: var(--calliope-radius-md);
  cursor: pointer;
  text-align: left;
  font-family: var(--calliope-font-mono);
  transition: background-color var(--calliope-duration-fast)
    var(--calliope-ease-out);
}

.mention-menu__item.is-highlighted {
  background: var(--calliope-overlay-hover);
}

.mention-menu__title {
  font-size: 0.82rem;
  color: var(--calliope-paper);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.mention-menu__path {
  font-size: 0.68rem;
  color: var(--calliope-paper-dim);
  white-space: nowrap;
  letter-spacing: 0.02em;
  flex-shrink: 0;
}
</style>
