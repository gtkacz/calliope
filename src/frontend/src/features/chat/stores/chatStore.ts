import { defineStore } from "pinia";

import * as chatApi from "../api";
import { listDocuments } from "@/features/documents/api";
import type { DocumentSummary } from "@/features/documents/types";
import type {
  CanonPolicy,
  ComposerMode,
  ConversationFolder,
  MessageRead,
  SessionSummary,
} from "../types";

interface ChatState {
  folders: ConversationFolder[];
  sessions: SessionSummary[];
  activeSessionId: string | null;
  messages: MessageRead[];
  mode: ComposerMode;
  policy: CanonPolicy;
  selectedWorkspaceId: string | null;
  selectedChatProfileId: string | null;
  pending: boolean;
  pendingSince: number | null;
  errorMessage: string | null;
  mentionDocuments: DocumentSummary[];
  mentionWorkspaceId: string | null;
  citedDocumentIds: string[];
  canvas: string;
}

export const useChatStore = defineStore("chat", {
  state: (): ChatState => ({
    folders: [],
    sessions: [],
    activeSessionId: null,
    messages: [],
    mode: "chat",
    policy: "strict_canon",
    selectedWorkspaceId: null,
    selectedChatProfileId: null,
    pending: false,
    pendingSince: null,
    errorMessage: null,
    mentionDocuments: [],
    mentionWorkspaceId: null,
    citedDocumentIds: [],
    canvas: "",
  }),
  getters: {
    canSubmit(state): boolean {
      if (state.pending || state.selectedWorkspaceId === null) return false;
      if (
        (state.mode === "chat" || state.mode === "write") &&
        state.selectedChatProfileId === null
      ) {
        return false;
      }
      return true;
    },
    unfiledSessions(state): SessionSummary[] {
      return state.sessions.filter((session) => session.folder_id === null);
    },
  },
  actions: {
    async refreshConversationList() {
      const [folders, sessions] = await Promise.all([
        chatApi.listFolders(),
        chatApi.listSessions(this.selectedWorkspaceId),
      ]);
      this.folders = folders;
      this.sessions = sessions;
    },
    async openSession(sessionId: string) {
      const detail = await chatApi.getSession(sessionId);
      this.activeSessionId = detail.id;
      this.messages = detail.messages;
      this.canvas = detail.canvas ?? "";
    },
    async deleteSession(sessionId: string) {
      await chatApi.deleteSession(sessionId);
      this.sessions = this.sessions.filter(
        (session) => session.id !== sessionId,
      );
      if (this.activeSessionId === sessionId) {
        this.activeSessionId = null;
        this.messages = [];
      }
    },
    async loadMentionDocuments() {
      const workspaceId = this.selectedWorkspaceId;
      if (workspaceId === null) {
        this.mentionDocuments = [];
        this.mentionWorkspaceId = null;
        return;
      }
      this.mentionDocuments = [];
      this.mentionWorkspaceId = workspaceId;
      try {
        const documents = await listDocuments(workspaceId);
        if (this.selectedWorkspaceId !== workspaceId) return;
        this.mentionDocuments = documents;
      } catch {
        // Swallow errors — mention suggestions are best-effort
      }
    },
    async submitMessage(text: string) {
      const trimmed = text.trim();
      if (trimmed.length === 0 || !this.canSubmit) return;
      this.pending = true;
      this.pendingSince = Date.now();
      this.errorMessage = null;
      try {
        if (this.mode === "chat") {
          const mentionDocuments =
            this.mentionWorkspaceId === this.selectedWorkspaceId
              ? this.mentionDocuments
              : [];
          // Keep only citations whose document path still appears as an @<path> token
          const reconciledIds = this.citedDocumentIds.filter((id) => {
            const doc = mentionDocuments.find((d) => d.id === id);
            return doc !== undefined && trimmed.includes(`@${doc.path}`);
          });
          const response = await chatApi.sendChat({
            message: trimmed,
            policy: this.policy,
            session_id: this.activeSessionId,
            workspace_id: this.selectedWorkspaceId,
            chat_profile_id: this.selectedChatProfileId as string,
            limit: 8,
            cited_document_ids: reconciledIds,
          });
          this.citedDocumentIds = [];
          this.activeSessionId = response.session.id;
          this.upsertSession(response.session);
          this.messages.push(response.user_message, response.assistant_message);
        } else if (this.mode === "write") {
          const mentionDocuments =
            this.mentionWorkspaceId === this.selectedWorkspaceId
              ? this.mentionDocuments
              : [];
          const reconciledIds = this.citedDocumentIds.filter((id) => {
            const doc = mentionDocuments.find((d) => d.id === id);
            return doc !== undefined && trimmed.includes(`@${doc.path}`);
          });
          const response = await chatApi.sendWrite({
            message: trimmed,
            canvas: this.canvas,
            policy: this.policy,
            session_id: this.activeSessionId,
            workspace_id: this.selectedWorkspaceId,
            chat_profile_id: this.selectedChatProfileId as string,
            limit: 8,
            cited_document_ids: reconciledIds,
          });
          this.citedDocumentIds = [];
          this.canvas = response.canvas;
          this.activeSessionId = response.session.id;
          this.upsertSession(response.session);
          this.messages.push(response.user_message, response.assistant_message);
        } else {
          const response = await chatApi.sendSearch({
            query: trimmed,
            session_id: this.activeSessionId,
            workspace_id: this.selectedWorkspaceId,
            limit: 8,
            persist: true,
          });
          if (response.session !== null) {
            this.activeSessionId = response.session.id;
            this.upsertSession(response.session);
          }
          if (response.search_message !== null) {
            this.messages.push(response.search_message);
          }
        }
      } catch (error) {
        this.errorMessage =
          error instanceof Error ? error.message : "Request failed.";
      } finally {
        this.pending = false;
        this.pendingSince = null;
      }
    },
    upsertSession(session: SessionSummary) {
      const index = this.sessions.findIndex(
        (existing) => existing.id === session.id,
      );
      if (index === -1) this.sessions.unshift(session);
      else this.sessions.splice(index, 1, session);
    },
    async saveCanvas() {
      if (this.activeSessionId === null) return;
      try {
        await chatApi.patchSession(this.activeSessionId, {
          canvas: this.canvas,
        });
      } catch {
        // Best-effort: autosave must never block editing
      }
    },
  },
});
