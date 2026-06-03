import { requestJson } from "@/shared/api/client";
import type { DirectoryListing } from "@/features/workspaces/types";

import type { EditMode, EditProposal, FileContent } from "./types";

export type { DirectoryListing };

interface ProposeEditParams {
  path: string;
  instruction: string;
  mode: EditMode;
  chat_profile_id: string;
  apply_guidelines: boolean;
}

export function readFile(path: string): Promise<FileContent> {
  return requestJson(`/v1/filesystem/read?path=${encodeURIComponent(path)}`);
}

export function writeFile(path: string, content: string): Promise<FileContent> {
  return requestJson("/v1/filesystem/write", {
    method: "PUT",
    body: JSON.stringify({ path, content }),
  });
}

export function proposeEdit(params: ProposeEditParams): Promise<EditProposal> {
  return requestJson("/v1/editor/propose", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function listDir(
  path: string,
  includeFiles = true,
): Promise<DirectoryListing> {
  const params = new URLSearchParams({
    path,
    include_files: String(includeFiles),
  });
  return requestJson(`/v1/filesystem/list?${params.toString()}`);
}
