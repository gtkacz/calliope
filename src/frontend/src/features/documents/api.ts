import { requestJson } from "@/shared/api/client";

import type { DocumentContent, DocumentSummary } from "./types";

export function listDocuments(workspaceId: string): Promise<DocumentSummary[]> {
  return requestJson(
    `/v1/documents?workspace_id=${encodeURIComponent(workspaceId)}`,
  );
}

export function getDocumentContent(
  documentId: string,
  chunkId: string | null = null,
): Promise<DocumentContent> {
  const query =
    chunkId === null ? "" : `?chunk_id=${encodeURIComponent(chunkId)}`;
  return requestJson(
    `/v1/documents/${encodeURIComponent(documentId)}/content${query}`,
  );
}
