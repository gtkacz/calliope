export type CanonPolicy = 'strict_canon' | 'canon_plus_inference' | 'creative_but_consistent'
export type ComposerMode = 'chat' | 'search' | 'write'

export interface SourceReference {
  document_id: string
  chunk_id: string
  path: string
  heading: string
  excerpt: string
  score: number
}

export interface ConversationFolder {
  id: string
  name: string
  parent_id: string | null
  position: number
  created_at: string
  updated_at: string
}

export interface SessionSummary {
  id: string
  title: string | null
  folder_id: string | null
  workspace_id: string | null
  created_at: string
  updated_at: string
}

export interface MessageRead {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'search' | string
  content: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface SessionDetail extends SessionSummary {
  messages: MessageRead[]
  canvas: string | null
}

export interface ChatResponse {
  session: SessionSummary
  user_message: MessageRead
  assistant_message: MessageRead
  answer: string
  sources: SourceReference[]
  trace_id: string
}

export interface SearchResponse {
  sources: SourceReference[]
  session: SessionSummary | null
  search_message: MessageRead | null
}

export interface WriteResponse {
  session: SessionSummary
  user_message: MessageRead
  assistant_message: MessageRead
  canvas: string
  sources: SourceReference[]
  trace_id: string
}
