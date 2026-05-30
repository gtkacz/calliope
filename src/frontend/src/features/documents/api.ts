import { requestJson } from "@/shared/api/client";

import type { DocumentSummary } from "./types";

export function listDocuments(workspaceId: string): Promise<DocumentSummary[]> {
  return requestJson(
    `/v1/documents?workspace_id=${encodeURIComponent(workspaceId)}`,
  );
}
