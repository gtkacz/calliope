export interface Workspace {
  id: string
  name: string
  root_path: string
  include_globs: string[]
  exclude_globs: string[]
  guidelines: string | null
  created_at: string
}

export interface ReindexResponse {
  documents_indexed: number
  chunks_indexed: number
}

export interface GlobPreviewBucket {
  count: number
  paths: string[]
}

export interface GlobPreview {
  visited_count: number
  included: GlobPreviewBucket
  ignored: GlobPreviewBucket
  truncated: boolean
}

export interface DirectoryEntry {
  name: string
  path: string
  is_dir: boolean
  is_hidden: boolean
}

export interface DirectoryListing {
  path: string
  parent: string | null
  entries: DirectoryEntry[]
  browse_root: string | null
}
