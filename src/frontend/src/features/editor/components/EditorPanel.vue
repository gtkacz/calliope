<script setup lang="ts">
import { computed, ref } from "vue";

import { ApiError } from "@/shared/api/client";
import { useChatStore } from "@/features/chat/stores/chatStore";
import { useWorkspaceStore } from "@/features/workspaces/stores/workspaceStore";

import { proposeEdit, readFile, writeFile } from "../api";
import type { EditMode, EditProposal, FileContent } from "../types";
import MarkdownFilePicker from "./MarkdownFilePicker.vue";

interface Props {
  open: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  "update:open": [value: boolean];
}>();

const chat = useChatStore();
const workspace = useWorkspaceStore();

const pickerOpen = ref(false);
const loadedFile = ref<FileContent | null>(null);
const proposal = ref<EditProposal | null>(null);
const instruction = ref("");
const mode = ref<EditMode>("append");
const isProposing = ref(false);
const isSaving = ref(false);
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);

const workspaceRoot = computed<string>(
  () => workspace.selectedWorkspace?.root_path ?? "/",
);

const canPropose = computed<boolean>(
  () =>
    loadedFile.value !== null &&
    instruction.value.trim().length > 0 &&
    chat.selectedChatProfileId !== null &&
    !isProposing.value,
);

function openPicker(): void {
  pickerOpen.value = true;
}

async function onFileSelected(path: string): Promise<void> {
  errorMessage.value = null;
  successMessage.value = null;
  proposal.value = null;
  instruction.value = "";
  try {
    loadedFile.value = await readFile(path);
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof ApiError ? error.message : "Failed to read file.";
  }
}

async function propose(): Promise<void> {
  if (
    !canPropose.value ||
    chat.selectedChatProfileId === null ||
    loadedFile.value === null
  ) {
    return;
  }
  isProposing.value = true;
  errorMessage.value = null;
  successMessage.value = null;
  try {
    proposal.value = await proposeEdit({
      path: loadedFile.value.path,
      instruction: instruction.value.trim(),
      mode: mode.value,
      chat_profile_id: chat.selectedChatProfileId,
    });
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof ApiError ? error.message : "Proposal failed.";
  } finally {
    isProposing.value = false;
  }
}

async function save(): Promise<void> {
  if (proposal.value === null) {
    return;
  }
  isSaving.value = true;
  errorMessage.value = null;
  try {
    const saved = await writeFile(
      proposal.value.path,
      proposal.value.proposed_content,
    );
    // Refresh shown content and clear the proposal after a successful save.
    loadedFile.value = saved;
    proposal.value = null;
    instruction.value = "";
    successMessage.value = "File saved.";
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof ApiError ? error.message : "Save failed.";
  } finally {
    isSaving.value = false;
  }
}

function discard(): void {
  proposal.value = null;
  errorMessage.value = null;
}

function close(): void {
  emit("update:open", false);
}

const modeOptions: { value: EditMode; label: string }[] = [
  { value: "append", label: "Append" },
  { value: "rewrite", label: "Rewrite" },
];
</script>

<template>
  <v-navigation-drawer
    :model-value="props.open"
    location="right"
    temporary
    :width="480"
    class="editor-panel"
    @update:model-value="(value) => emit('update:open', value)"
  >
    <div class="editor-panel__inner">
      <header class="editor-panel__head">
        <div class="editor-panel__head-text">
          <span class="calliope-eyebrow">File editor</span>
          <h2 class="editor-panel__title calliope-serif">Edit a file</h2>
        </div>
        <button
          type="button"
          class="editor-panel__close"
          aria-label="Close editor panel"
          @click="close"
        >
          <v-icon icon="$mdi-close" size="18" />
        </button>
      </header>

      <div class="editor-panel__section">
        <div class="editor-panel__file-row">
          <span
            v-if="loadedFile"
            class="editor-panel__file-path calliope-mono"
            :title="loadedFile.path"
          >
            {{ loadedFile.path }}
          </span>
          <span v-else class="editor-panel__file-placeholder"
            >No file selected</span
          >
          <button
            type="button"
            class="editor-panel__btn editor-panel__btn--ghost"
            @click="openPicker"
          >
            <v-icon icon="$mdi-folder-open-outline" size="15" />
            {{ loadedFile ? "Change" : "Choose file" }}
          </button>
        </div>
      </div>

      <template v-if="loadedFile && !proposal">
        <div class="editor-panel__section editor-panel__section--grow">
          <div class="editor-panel__label calliope-eyebrow">
            Current content
          </div>
          <pre class="editor-panel__content-pane">{{ loadedFile.content }}</pre>
        </div>

        <div class="editor-panel__section">
          <div class="editor-panel__label calliope-eyebrow">Mode</div>
          <div
            class="editor-panel__mode-toggle"
            role="group"
            aria-label="Edit mode"
          >
            <button
              v-for="opt in modeOptions"
              :key="opt.value"
              type="button"
              class="editor-panel__mode-btn"
              :class="{ 'editor-panel__mode-btn--active': mode === opt.value }"
              @click="mode = opt.value"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <div class="editor-panel__section">
          <div class="editor-panel__label calliope-eyebrow">Instruction</div>
          <v-textarea
            v-model="instruction"
            :rows="4"
            variant="plain"
            hide-details
            placeholder="Describe what to change…"
            class="editor-panel__instruction"
          />
        </div>

        <div v-if="!chat.selectedChatProfileId" class="editor-panel__section">
          <v-alert
            type="warning"
            variant="tonal"
            density="compact"
            border="start"
          >
            Select a chat profile to enable proposals.
          </v-alert>
        </div>

        <div v-if="errorMessage" class="editor-panel__section">
          <v-alert
            type="error"
            variant="tonal"
            density="compact"
            border="start"
          >
            {{ errorMessage }}
          </v-alert>
        </div>

        <div v-if="successMessage" class="editor-panel__section">
          <v-alert
            type="success"
            variant="tonal"
            density="compact"
            border="start"
          >
            {{ successMessage }}
          </v-alert>
        </div>

        <footer class="editor-panel__foot">
          <button
            type="button"
            class="editor-panel__btn editor-panel__btn--primary"
            :disabled="!canPropose"
            @click="propose"
          >
            <v-progress-circular
              v-if="isProposing"
              size="14"
              width="2"
              indeterminate
            />
            <span v-else>Propose</span>
          </button>
        </footer>
      </template>

      <template v-else-if="proposal">
        <div class="editor-panel__section editor-panel__section--grow">
          <div class="editor-panel__diff">
            <div
              class="editor-panel__diff-pane editor-panel__diff-pane--before"
            >
              <div class="editor-panel__label calliope-eyebrow">Current</div>
              <pre class="editor-panel__content-pane">{{
                proposal.original_content
              }}</pre>
            </div>
            <div class="editor-panel__diff-pane editor-panel__diff-pane--after">
              <div class="editor-panel__label calliope-eyebrow">Proposed</div>
              <pre
                class="editor-panel__content-pane editor-panel__content-pane--proposed"
                >{{ proposal.proposed_content }}</pre
              >
            </div>
          </div>
        </div>

        <div v-if="errorMessage" class="editor-panel__section">
          <v-alert
            type="error"
            variant="tonal"
            density="compact"
            border="start"
          >
            {{ errorMessage }}
          </v-alert>
        </div>

        <footer class="editor-panel__foot editor-panel__foot--proposal">
          <button
            type="button"
            class="editor-panel__btn editor-panel__btn--ghost"
            @click="discard"
          >
            Discard
          </button>
          <button
            type="button"
            class="editor-panel__btn editor-panel__btn--primary"
            :disabled="isSaving"
            @click="save"
          >
            <v-progress-circular
              v-if="isSaving"
              size="14"
              width="2"
              indeterminate
            />
            <span v-else>Save to file</span>
          </button>
        </footer>
      </template>
    </div>
  </v-navigation-drawer>

  <MarkdownFilePicker
    v-model="pickerOpen"
    :initial-path="workspaceRoot"
    @select="onFileSelected"
  />
</template>

<style scoped>
.editor-panel :deep(.v-navigation-drawer__content) {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.editor-panel__inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--calliope-ink-soft);
  overflow: hidden;
}

.editor-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: var(--calliope-space-md) var(--calliope-space-lg) var(--calliope-space-sm);
  border-bottom: 1px solid var(--calliope-border);
  flex-shrink: 0;
}

.editor-panel__head-text {
  display: flex;
  flex-direction: column;
  gap: var(--calliope-space-2xs);
}

.editor-panel__title {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 380;
  color: var(--calliope-paper);
  letter-spacing: -0.012em;
}

.editor-panel__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: none;
  border: 1px solid transparent;
  border-radius: var(--calliope-radius-sm);
  color: var(--calliope-paper-dim);
  cursor: pointer;
  margin-top: 0.1rem;
  transition:
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    background-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.editor-panel__close:hover {
  color: var(--calliope-paper);
  border-color: var(--calliope-border);
  background: var(--calliope-overlay-hover);
}

.editor-panel__section {
  padding: var(--calliope-space-sm) var(--calliope-space-lg);
  border-bottom: 1px solid var(--calliope-border);
  flex-shrink: 0;
}

.editor-panel__section--grow {
  flex: 1 1 auto;
  overflow-y: auto;
  min-height: 0;
}

.editor-panel__label {
  margin-bottom: 0.45rem;
  color: var(--calliope-paper-dim);
}

.editor-panel__file-row {
  display: flex;
  align-items: center;
  gap: var(--calliope-space-sm);
}

.editor-panel__file-path {
  flex: 1 1 auto;
  font-size: 0.78rem;
  color: var(--calliope-paper);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.editor-panel__file-placeholder {
  flex: 1 1 auto;
  font-size: 0.83rem;
  color: var(--calliope-paper-dim);
}

.editor-panel__content-pane {
  font-family: var(--calliope-font-mono);
  font-size: 0.78rem;
  line-height: 1.6;
  color: var(--calliope-paper-muted);
  background: var(--calliope-ink);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-sm);
  padding: 0.75rem 1rem;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 240px;
  margin: 0;
}

.editor-panel__content-pane--proposed {
  border-color: var(--calliope-bronze-glow);
  color: var(--calliope-paper);
}

.editor-panel__mode-toggle {
  display: inline-flex;
  gap: 0;
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-sm);
  overflow: hidden;
}

.editor-panel__mode-btn {
  font-family: var(--calliope-font-body);
  font-size: 0.8rem;
  font-weight: 500;
  padding: 0.4rem 0.9rem;
  background: transparent;
  border: none;
  border-right: 1px solid var(--calliope-border);
  color: var(--calliope-paper-muted);
  cursor: pointer;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.editor-panel__mode-btn:last-child {
  border-right: none;
}

.editor-panel__mode-btn--active {
  background: var(--calliope-bronze-veil);
  color: var(--calliope-bronze);
}

.editor-panel__mode-btn:hover:not(.editor-panel__mode-btn--active) {
  background: var(--calliope-overlay-hover);
  color: var(--calliope-paper);
}

.editor-panel__instruction :deep(.v-field) {
  background: var(--calliope-ink);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-sm);
  padding: 0.25rem 0.75rem;
  transition:
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    box-shadow var(--calliope-duration-fast) var(--calliope-ease-out);
}

.editor-panel__instruction :deep(.v-field--focused) {
  border-color: var(--calliope-bronze);
  box-shadow: 0 0 0 1px var(--calliope-bronze-glow);
}

.editor-panel__instruction :deep(.v-field__input),
.editor-panel__instruction :deep(textarea) {
  font-family: var(--calliope-font-body);
  font-size: 0.88rem;
  line-height: 1.55;
  color: var(--calliope-paper);
}

.editor-panel__diff {
  display: flex;
  flex-direction: column;
  gap: var(--calliope-space-md);
}

.editor-panel__diff-pane {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.editor-panel__foot {
  display: flex;
  justify-content: flex-end;
  padding: var(--calliope-space-md) var(--calliope-space-lg);
  border-top: 1px solid var(--calliope-border);
  background: var(--calliope-ink-soft);
  flex-shrink: 0;
  margin-top: auto;
}

.editor-panel__foot--proposal {
  gap: var(--calliope-space-xs);
}

.editor-panel__btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-family: var(--calliope-font-body);
  font-size: 0.83rem;
  font-weight: 500;
  letter-spacing: 0.01em;
  padding: 0.55rem 1.1rem;
  border-radius: var(--calliope-radius-sm);
  cursor: pointer;
  border: 1px solid transparent;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.editor-panel__btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.editor-panel__btn--ghost {
  background: transparent;
  color: var(--calliope-paper-muted);
  border-color: var(--calliope-border);
}

.editor-panel__btn--ghost:not(:disabled):hover {
  color: var(--calliope-paper);
  border-color: var(--calliope-border-strong);
  background: var(--calliope-overlay-hover);
}

.editor-panel__btn--primary {
  background: var(--calliope-bronze);
  color: var(--calliope-ink);
}

.editor-panel__btn--primary:not(:disabled):hover {
  background: var(--calliope-bronze-deep);
}
</style>
