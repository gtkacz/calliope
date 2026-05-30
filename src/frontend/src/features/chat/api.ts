import { requestJson } from "@/shared/api/client";

import type {
  CanonPolicy,
  ChatResponse,
  ConversationFolder,
  SearchResponse,
  SessionDetail,
  SessionSummary,
} from "./types";

export function listSessions(): Promise<SessionSummary[]> {
  return requestJson("/v1/sessions");
}

export function getSession(sessionId: string): Promise<SessionDetail> {
  return requestJson(`/v1/sessions/${sessionId}`);
}

export function patchSession(
  sessionId: string,
  payload: { title?: string; folder_id?: string | null },
): Promise<SessionSummary> {
  return requestJson(`/v1/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteSession(sessionId: string): Promise<void> {
  return requestJson(`/v1/sessions/${sessionId}`, { method: "DELETE" });
}

export function listFolders(): Promise<ConversationFolder[]> {
  return requestJson("/v1/conversation-folders");
}

export function createFolder(payload: {
  name: string;
  parent_id: string | null;
  position: number;
}): Promise<ConversationFolder> {
  return requestJson("/v1/conversation-folders", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function patchFolder(
  folderId: string,
  payload: { name?: string; parent_id?: string | null; position?: number },
): Promise<ConversationFolder> {
  return requestJson(`/v1/conversation-folders/${folderId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteFolder(folderId: string): Promise<void> {
  return requestJson(`/v1/conversation-folders/${folderId}`, {
    method: "DELETE",
  });
}

export function sendChat(payload: {
  message: string;
  policy: CanonPolicy;
  session_id: string | null;
  workspace_id: string | null;
  chat_profile_id: string;
  limit: number;
  cited_document_ids: string[];
}): Promise<ChatResponse> {
  return requestJson("/v1/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function sendSearch(payload: {
  query: string;
  session_id: string | null;
  workspace_id: string | null;
  limit: number;
  persist: true;
}): Promise<SearchResponse> {
  return requestJson("/v1/search", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
