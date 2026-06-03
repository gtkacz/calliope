export type ProfileKind = 'openai_compatible' | 'ollama' | 'koboldcpp'
export type ProfileCapability = 'chat' | 'embeddings' | 'rerank' | 'streaming'

export interface Profile {
  id: string
  name: string
  kind: ProfileKind
  base_url: string
  model: string
  api_key_ref: string | null
  capabilities: ProfileCapability[]
  max_tokens: number | null
  created_at: string
}
