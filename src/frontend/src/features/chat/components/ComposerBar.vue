<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import { Motion } from "motion-v";

import type { CanonPolicy, ComposerMode } from "../types";
import type { Profile } from "@/features/profiles/types";
import type { Workspace } from "@/features/workspaces/types";
import type { DocumentSummary } from "@/features/documents/types";
import { useChatStore } from "../stores/chatStore";
import MentionMenu from "./MentionMenu.vue";

const props = defineProps<{
  mode: ComposerMode;
  policy: CanonPolicy;
  selectedWorkspaceId: string | null;
  selectedChatProfileId: string | null;
  workspaces: Workspace[];
  profiles: Profile[];
  pending: boolean;
  disabled: boolean;
}>();

const emit = defineEmits<{
  "update:mode": [value: ComposerMode];
  "update:policy": [value: CanonPolicy];
  "update:selectedWorkspaceId": [value: string | null];
  "update:selectedChatProfileId": [value: string | null];
  submit: [value: string];
}>();

const chat = useChatStore();

const text = ref("");
const focused = ref(false);
const mentionMenuRef = ref<InstanceType<typeof MentionMenu> | null>(null);
const inputRef = ref<{ focus: () => void } | null>(null);

// Track whether documents have been loaded for the current open of the mention menu
let mentionDocumentsLoaded = false;

// The active @token start position in the textarea, or -1 when no mention is open
const activeMentionStart = ref(-1);

const mentionQuery = computed(() => {
  if (activeMentionStart.value === -1) return "";
  // Slice from the character after '@' to end; the menu component does its own filtering
  return text.value.slice(activeMentionStart.value + 1);
});

const mentionOpen = computed(() => activeMentionStart.value !== -1);

// Icon-only canon-policy radio. Each segment's tooltip carries the full
// explanation; the icon alone reads at a glance once learned.
const policyOptions: {
  value: CanonPolicy;
  icon: string;
  label: string;
  description: string;
}[] = [
  {
    value: "strict_canon",
    icon: "$mdi-shield-check-outline",
    label: "Strict canon",
    description:
      "Strict canon — answer only from what your notes explicitly state. No inference, no embellishment.",
  },
  {
    value: "canon_plus_inference",
    icon: "$mdi-scale-balance",
    label: "Canon + inference",
    description:
      "Canon + inference — stay grounded in your notes, but allow reasonable conclusions that follow from them.",
  },
  {
    value: "creative_but_consistent",
    icon: "$mdi-fountain-pen-tip",
    label: "Creative, consistent",
    description:
      "Creative, consistent — invent freely while staying consistent with everything established in canon.",
  },
];

const disabledReason = computed(() => {
  if (props.pending) return "Waiting for response";
  if (props.workspaces.length === 0) return "Workspace required";
  if (props.mode === "chat" && props.profiles.length === 0)
    return "Chat profile required";
  return null;
});

const canSubmit = computed(
  () => !props.disabled && text.value.trim().length > 0,
);

const citedDocs = computed<DocumentSummary[]>(() =>
  chat.citedDocumentIds
    .map((id) => chat.mentionDocuments.find((d) => d.id === id))
    .filter((d): d is DocumentSummary => d !== undefined),
);

function detectMention(caretPos: number) {
  // Walk backwards from the caret to find an uninterrupted @word token
  const before = text.value.slice(0, caretPos);
  const match = /(?:^|[\s\n])(@\S*)$/.exec(before);
  if (match !== null) {
    // The '@' position within the full text
    activeMentionStart.value = caretPos - match[1].length;
  } else {
    activeMentionStart.value = -1;
    mentionDocumentsLoaded = false;
  }
}

function onInput(event: Event) {
  const target = event.target as HTMLTextAreaElement;
  detectMention(target.selectionStart ?? text.value.length);
  if (mentionOpen.value && !mentionDocumentsLoaded) {
    mentionDocumentsLoaded = true;
    chat.loadMentionDocuments();
  }
}

function onKeydown(event: KeyboardEvent) {
  if (mentionOpen.value) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      mentionMenuRef.value?.moveHighlight(1);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      mentionMenuRef.value?.moveHighlight(-1);
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      mentionMenuRef.value?.selectHighlighted();
      return;
    }
    if (event.key === "Escape") {
      activeMentionStart.value = -1;
      mentionDocumentsLoaded = false;
      return;
    }
  }
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    submit();
  }
}

function onSelectMention(doc: DocumentSummary) {
  // Replace the active @token with the full @<path> and a trailing space
  const before = text.value.slice(0, activeMentionStart.value);
  const after = text.value.slice(
    activeMentionStart.value + 1 + mentionQuery.value.length,
  );
  text.value = `${before}@${doc.path} ${after}`;
  activeMentionStart.value = -1;
  mentionDocumentsLoaded = false;

  // Dedup before pushing
  if (!chat.citedDocumentIds.includes(doc.id)) {
    chat.citedDocumentIds = [...chat.citedDocumentIds, doc.id];
  }
}

function removeCitation(id: string) {
  chat.citedDocumentIds = chat.citedDocumentIds.filter(
    (existing) => existing !== id,
  );
}

function submit() {
  const value = text.value.trim();
  if (value.length === 0 || props.disabled) return;
  emit("submit", value);
  text.value = "";
  activeMentionStart.value = -1;
  mentionDocumentsLoaded = false;
}

function setMode(next: ComposerMode) {
  if (next === props.mode) return;
  emit("update:mode", next);
}

// Prefill the composer from an empty-state seed prompt, then focus so the
// writer can edit before sending — deliberately does not auto-submit.
function prefill(value: string) {
  text.value = value;
  nextTick(() => inputRef.value?.focus());
}

defineExpose({ prefill });
</script>

<template>
  <div class="composer-wrap">
    <div class="composer" :class="{ 'is-focused': focused }">
      <div v-if="citedDocs.length > 0" class="composer__citations">
        <span
          v-for="doc in citedDocs"
          :key="doc.id"
          class="composer__citation calliope-mono"
        >
          <v-icon size="11" icon="$mdi-file-document-outline" class="composer__citation-icon" aria-hidden="true" />
          @{{ doc.title || doc.path }}
          <button
            type="button"
            class="composer__citation-remove"
            :aria-label="`Remove citation ${doc.title || doc.path}`"
            @click="removeCitation(doc.id)"
          >
            ×
          </button>
        </span>
      </div>

      <div class="composer__input-wrap">
        <MentionMenu
          v-if="mentionOpen"
          ref="mentionMenuRef"
          :documents="chat.mentionDocuments"
          :query="mentionQuery"
          @select="onSelectMention"
        />
        <v-textarea
          ref="inputRef"
          v-model="text"
          rows="1"
          auto-grow
          variant="plain"
          density="comfortable"
          hide-details
          placeholder="Ask Calliope, or search your notes…"
          class="composer__input"
          @focus="focused = true"
          @blur="focused = false"
          @input="onInput"
          @keydown="onKeydown"
        />
      </div>

      <div class="composer__controls">
        <div
          class="composer__segmented"
          role="tablist"
          aria-label="Composer mode"
        >
          <button
            type="button"
            class="composer__segment"
            :class="{ 'is-active': mode === 'chat' }"
            role="tab"
            :aria-selected="mode === 'chat'"
            @click="setMode('chat')"
          >
            Chat
          </button>
          <button
            type="button"
            class="composer__segment"
            :class="{ 'is-active': mode === 'search' }"
            role="tab"
            :aria-selected="mode === 'search'"
            @click="setMode('search')"
          >
            Search
          </button>
        </div>

        <div class="composer__pills">
          <div
            class="composer__policy"
            role="radiogroup"
            aria-label="Canon policy"
          >
            <v-tooltip
              v-for="option in policyOptions"
              :key="option.value"
              :text="option.description"
              location="top"
              :open-delay="120"
              max-width="252"
            >
              <template #activator="{ props: tipProps }">
                <button
                  v-bind="tipProps"
                  type="button"
                  class="composer__policy-seg"
                  :class="{ 'is-active': policy === option.value }"
                  role="radio"
                  :aria-checked="policy === option.value"
                  :aria-label="option.label"
                  @click="emit('update:policy', option.value)"
                >
                  <v-icon :icon="option.icon" size="17" />
                </button>
              </template>
            </v-tooltip>
          </div>
          <v-select
            :model-value="selectedWorkspaceId"
            :items="workspaces"
            item-title="name"
            item-value="id"
            variant="plain"
            density="compact"
            hide-details
            placeholder="Workspace"
            class="composer__pill"
            menu-icon="$mdi-chevron-down"
            aria-label="Workspace"
            @update:model-value="emit('update:selectedWorkspaceId', $event)"
          />
          <v-select
            :model-value="selectedChatProfileId"
            :disabled="mode === 'search'"
            :items="profiles"
            item-title="name"
            item-value="id"
            variant="plain"
            density="compact"
            hide-details
            placeholder="Model"
            class="composer__pill"
            menu-icon="$mdi-chevron-down"
            aria-label="Chat profile"
            @update:model-value="emit('update:selectedChatProfileId', $event)"
          />
        </div>

        <Motion
          tag="div"
          class="composer__send-wrap"
          :while-hover="canSubmit ? { scale: 1.06 } : undefined"
          :while-press="canSubmit ? { scale: 0.92 } : undefined"
          :transition="{ type: 'spring', stiffness: 420, damping: 20 }"
        >
          <button
            type="button"
            class="composer__send"
            :class="{ 'is-active': canSubmit, 'is-pending': pending }"
            :disabled="!canSubmit"
            aria-label="Submit"
            @click="submit"
          >
            <v-icon v-if="!pending" icon="$mdi-arrow-up" size="20" />
            <span v-else class="composer__send-spinner" aria-hidden="true" />
          </button>
        </Motion>
      </div>
    </div>

    <p v-if="disabledReason" class="composer__hint calliope-mono">
      {{ disabledReason }}
    </p>
  </div>
</template>

<style scoped>
.composer-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding: var(--calliope-space-sm) var(--calliope-space-xl) var(--calliope-space-md);
  background: var(--calliope-ink-soft);
  border-top: 1px solid var(--calliope-border-strong);
}

.composer {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  padding: 0.85rem 1rem 0.75rem 1.15rem;
  background: var(--calliope-ink-raised);
  border: 1px solid var(--calliope-border-strong);
  border-radius: var(--calliope-radius-xl);
  box-shadow: var(--calliope-shadow-rest);
  transition:
    border-color var(--calliope-duration-base) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-base) var(--calliope-ease-out);
}

.composer.is-focused {
  border-color: var(--calliope-bronze);
  box-shadow:
    var(--calliope-shadow-rest),
    0 0 0 4px var(--calliope-bronze-veil);
}

.composer__input :deep(textarea) {
  font-family: var(--calliope-font-body);
  font-size: 0.97rem;
  line-height: 1.6;
  color: var(--calliope-paper);
  padding-top: 0.35rem;
}

.composer__input :deep(textarea::placeholder) {
  color: var(--calliope-paper-dim);
}

.composer__input :deep(.v-field__outline) {
  display: none;
}

.composer__controls {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.65rem;
}

.composer__segmented {
  display: inline-flex;
  padding: 0.2rem;
  background: var(--calliope-ink);
  border-radius: var(--calliope-radius-pill);
  border: 1px solid var(--calliope-border-strong);
}

.composer__segment {
  padding: 0.34rem 0.95rem;
  background: transparent;
  border: none;
  border-radius: var(--calliope-radius-pill);
  cursor: pointer;
  font-family: var(--calliope-font-body);
  font-size: 0.78rem;
  font-weight: 460;
  letter-spacing: 0.005em;
  color: var(--calliope-paper-dim);
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-fast) var(--calliope-ease-out);
}

.composer__segment:hover {
  color: var(--calliope-paper);
}

.composer__segment:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--calliope-bronze-veil);
}

/* Active tab reads unmistakably: gilt fill, dark ink text, and a soft bloom so
   it's obvious whether Chat or Search is selected. */
.composer__segment.is-active {
  background: var(--calliope-bronze);
  color: var(--calliope-ink);
  font-weight: 560;
  box-shadow: 0 0 10px 1px var(--calliope-bronze-glow);
}

.composer__segment.is-active:hover {
  color: var(--calliope-ink);
}

.composer__pills {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  justify-content: flex-end;
  min-width: 0;
}

/* Canon-policy radio: a single pill segmented into three icons. The container
   is the radiogroup; each icon is a radio whose selected state lifts to gilt. */
.composer__policy {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem;
  background: var(--calliope-ink);
  border: 1px solid var(--calliope-border-strong);
  border-radius: var(--calliope-radius-pill);
  flex: none;
}

.composer__policy-seg {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 26px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: var(--calliope-radius-pill);
  color: var(--calliope-paper-dim);
  cursor: pointer;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-fast) var(--calliope-ease-out);
}

.composer__policy-seg:hover {
  color: var(--calliope-paper);
}

.composer__policy-seg:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--calliope-bronze-veil);
}

.composer__policy-seg.is-active {
  background: var(--calliope-bronze);
  color: var(--calliope-ink);
  box-shadow: 0 0 9px 1px var(--calliope-bronze-glow);
}

.composer__pill {
  min-width: 0;
  max-width: 9.5rem;
}

.composer__pill :deep(.v-field) {
  padding: 0 0.6rem 0 0.85rem;
  background: var(--calliope-overlay-hover);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-pill);
  min-height: 28px;
  transition: border-color var(--calliope-duration-fast)
    var(--calliope-ease-out);
}

.composer__pill :deep(.v-field:hover),
.composer__pill :deep(.v-field--focused) {
  border-color: var(--calliope-border-strong);
}

.composer__pill :deep(.v-field__outline) {
  display: none;
}

.composer__pill :deep(.v-field__input) {
  padding: 0;
  min-height: 28px;
  font-family: var(--calliope-font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.02em;
  color: var(--calliope-paper);
}

.composer__pill :deep(.v-field__append-inner) {
  padding-top: 0;
  align-self: center;
}

.composer__pill :deep(.v-field__append-inner .v-icon) {
  opacity: 0.6;
  font-size: 1rem;
}

.composer__send-wrap {
  display: inline-flex;
}

.composer__send {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--calliope-ink-top);
  color: var(--calliope-paper-muted);
  border: 1px solid var(--calliope-border-strong);
  border-radius: 50%;
  cursor: pointer;
  /* Spring transition is driven by motion-v; CSS transition handles colour states */
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-base) var(--calliope-ease-out);
}

.composer__send.is-active {
  background: var(--calliope-bronze);
  color: var(--calliope-ink);
  border-color: var(--calliope-bronze);
  /* Warm gilt bloom — the "wax seal" glow evokes candlelight sealing a letter */
  box-shadow:
    0 0 0 3px var(--calliope-bronze-veil),
    0 0 14px 2px var(--calliope-bronze-glow);
}

.composer__send.is-active:hover {
  background: var(--calliope-bronze-deep);
  border-color: var(--calliope-bronze-deep);
  box-shadow:
    0 0 0 4px var(--calliope-bronze-veil),
    0 0 20px 4px var(--calliope-bronze-glow);
}

/* Disabled clearly reads as inert: dimmed, recessed, no gilt — so an empty
   composer (or a missing workspace/profile) visibly cannot be submitted. */
.composer__send:disabled {
  cursor: not-allowed;
  background: var(--calliope-ink-raised);
  color: var(--calliope-paper-dim);
  border-color: var(--calliope-border);
  opacity: 0.5;
  box-shadow: none;
}

@media (prefers-reduced-motion: reduce) {
  .composer__send {
    transition:
      background-color var(--calliope-duration-fast) var(--calliope-ease-out),
      color var(--calliope-duration-fast) var(--calliope-ease-out),
      border-color var(--calliope-duration-fast) var(--calliope-ease-out);
  }
  .composer__send-spinner {
    animation: none;
  }
}

.composer__send-spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--calliope-paper-muted);
  border-top-color: transparent;
  animation: calliope-spin 720ms linear infinite;
}

.composer__send.is-active.is-pending .composer__send-spinner {
  border-color: var(--calliope-ink);
  border-top-color: transparent;
}

@keyframes calliope-spin {
  to {
    transform: rotate(360deg);
  }
}

.composer__hint {
  margin: 0;
  padding-left: 0.25rem;
  color: var(--calliope-paper-dim);
  font-size: 0.7rem;
  letter-spacing: 0.06em;
}

.composer__input-wrap {
  position: relative;
}

.composer__citations {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--calliope-border);
}

.composer__citation {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.18rem 0.55rem;
  background: var(--calliope-bronze-veil);
  /* Editorial footnote pill: hairline gilt border evokes manuscript annotation marks */
  border: 1px solid var(--calliope-bronze-veil);
  border-radius: var(--calliope-radius-pill);
  font-family: var(--calliope-font-mono);
  font-size: 0.7rem;
  color: var(--calliope-bronze);
  letter-spacing: 0.02em;
  white-space: nowrap;
  transition:
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    background-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.composer__citation:hover {
  border-color: var(--calliope-bronze);
  background: var(--calliope-overlay-active);
}

.composer__citation-icon {
  color: var(--calliope-bronze);
  opacity: 0.75;
  flex-shrink: 0;
}

.composer__citation-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--calliope-paper-dim);
  font-size: 0.85rem;
  line-height: 1;
  padding: 0;
  transition: color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.composer__citation-remove:hover {
  color: var(--calliope-paper);
}

@media (max-width: 900px) {
  .composer__controls {
    grid-template-columns: 1fr auto;
    grid-template-rows: auto auto;
    gap: 0.5rem;
  }

  .composer__segmented {
    grid-row: 1;
  }

  .composer__pills {
    grid-column: 1 / -1;
    grid-row: 2;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .composer__send-wrap {
    grid-row: 1;
    grid-column: 2;
    justify-self: end;
  }
}
</style>
