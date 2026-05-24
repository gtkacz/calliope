import { requestJson } from '@/shared/api/client'

import type { DirectoryListing, ReindexResponse, Workspace } from './types'

export interface WorkspacePayload {
  name: string
  root_path: string
  include_globs: string[]
  exclude_globs: string[]
}

export function listWorkspaces(): Promise<Workspace[]> {
  return requestJson('/v1/workspaces')
}

export function getWorkspace(workspaceId: string): Promise<Workspace> {
  return requestJson(`/v1/workspaces/${workspaceId}`)
}

export function createWorkspace(payload: WorkspacePayload): Promise<Workspace> {
  return requestJson('/v1/workspaces', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function patchWorkspace(
  workspaceId: string,
  payload: Partial<WorkspacePayload>,
): Promise<Workspace> {
  return requestJson(`/v1/workspaces/${workspaceId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteWorkspace(workspaceId: string): Promise<void> {
  return requestJson(`/v1/workspaces/${workspaceId}`, { method: 'DELETE' })
}

export function reindexWorkspace(workspaceId: string): Promise<ReindexResponse> {
  return requestJson('/v1/reindex', {
    method: 'POST',
    body: JSON.stringify({ workspace_id: workspaceId }),
  })
}

export function listDirectory(path?: string): Promise<DirectoryListing> {
  const query = path ? `?path=${encodeURIComponent(path)}` : ''
  return requestJson(`/v1/filesystem/list${query}`)
}
