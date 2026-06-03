import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as chatApi from '../api'
import * as documentsApi from '@/features/documents/api'
import { useChatStore } from './chatStore'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.restoreAllMocks()
})

describe('chatStore', () => {
  it('loads folders and sessions', async () => {
    vi.spyOn(chatApi, 'listFolders').mockResolvedValue([
      {
        id: 'folder_1',
        name: 'Worldbuilding',
        parent_id: null,
        position: 0,
        created_at: '2026-05-20T12:00:00Z',
        updated_at: '2026-05-20T12:00:00Z',
      },
    ])
    vi.spyOn(chatApi, 'listSessions').mockResolvedValue([
      {
        id: 'session_1',
        title: 'Lake city',
        folder_id: 'folder_1',
        workspace_id: 'workspace_1',
        created_at: '2026-05-20T12:00:00Z',
        updated_at: '2026-05-20T12:05:00Z',
      },
    ])

    const store = useChatStore()
    await store.refreshConversationList()

    expect(store.folders).toHaveLength(1)
    expect(store.sessions[0].title).toBe('Lake city')
  })

  it('adds messages from chat response', async () => {
    vi.spyOn(chatApi, 'sendChat').mockResolvedValue({
      session: {
        id: 'session_1',
        title: 'Lake city',
        folder_id: null,
        workspace_id: 'workspace_1',
        created_at: '2026-05-20T12:00:00Z',
        updated_at: '2026-05-20T12:05:00Z',
      },
      user_message: {
        id: 'message_user',
        session_id: 'session_1',
        role: 'user',
        content: 'Question',
        metadata: { turn_kind: 'chat_user' },
        created_at: '2026-05-20T12:00:00Z',
      },
      assistant_message: {
        id: 'message_assistant',
        session_id: 'session_1',
        role: 'assistant',
        content: 'Answer',
        metadata: { turn_kind: 'assistant' },
        created_at: '2026-05-20T12:01:00Z',
      },
      answer: 'Answer',
      sources: [],
      trace_id: 'trace_1',
    })

    const store = useChatStore()
    store.selectedWorkspaceId = 'workspace_1'
    store.selectedChatProfileId = 'profile_1'
    await store.submitMessage('Question')

    expect(store.activeSessionId).toBe('session_1')
    expect(store.messages.map((message) => message.role)).toEqual(['user', 'assistant'])
  })

  it('does not send cited document ids loaded for another workspace', async () => {
    vi.spyOn(documentsApi, 'listDocuments').mockResolvedValue([
      {
        id: 'document_old',
        title: 'Old Note',
        path: 'old/note.md',
      },
    ])
    const sendChat = vi.spyOn(chatApi, 'sendChat').mockResolvedValue({
      session: {
        id: 'session_1',
        title: 'Lake city',
        folder_id: null,
        workspace_id: 'workspace_new',
        created_at: '2026-05-20T12:00:00Z',
        updated_at: '2026-05-20T12:05:00Z',
      },
      user_message: {
        id: 'message_user',
        session_id: 'session_1',
        role: 'user',
        content: 'Question',
        metadata: { turn_kind: 'chat_user' },
        created_at: '2026-05-20T12:00:00Z',
      },
      assistant_message: {
        id: 'message_assistant',
        session_id: 'session_1',
        role: 'assistant',
        content: 'Answer',
        metadata: { turn_kind: 'assistant' },
        created_at: '2026-05-20T12:01:00Z',
      },
      answer: 'Answer',
      sources: [],
      trace_id: 'trace_1',
    })

    const store = useChatStore()
    store.selectedWorkspaceId = 'workspace_old'
    await store.loadMentionDocuments()
    store.citedDocumentIds = ['document_old']
    store.selectedWorkspaceId = 'workspace_new'
    store.selectedChatProfileId = 'profile_1'

    await store.submitMessage('Use @old/note.md')

    expect(sendChat).toHaveBeenCalledWith(
      expect.objectContaining({ cited_document_ids: [] }),
    )
  })

  it('sends apply_guidelines true by default for chat', async () => {
    const sendChat = vi.spyOn(chatApi, 'sendChat').mockResolvedValue({
      session: {
        id: 'session_1',
        title: 'Lake city',
        folder_id: null,
        workspace_id: 'workspace_1',
        created_at: '2026-05-20T12:00:00Z',
        updated_at: '2026-05-20T12:05:00Z',
      },
      user_message: {
        id: 'message_user',
        session_id: 'session_1',
        role: 'user',
        content: 'Question',
        metadata: { turn_kind: 'chat_user' },
        created_at: '2026-05-20T12:00:00Z',
      },
      assistant_message: {
        id: 'message_assistant',
        session_id: 'session_1',
        role: 'assistant',
        content: 'Answer',
        metadata: { turn_kind: 'assistant' },
        created_at: '2026-05-20T12:01:00Z',
      },
      answer: 'Answer',
      sources: [],
      trace_id: 'trace_1',
    })

    const store = useChatStore()
    store.selectedWorkspaceId = 'workspace_1'
    store.selectedChatProfileId = 'profile_1'
    await store.submitMessage('Question')

    expect(sendChat).toHaveBeenCalledWith(
      expect.objectContaining({ apply_guidelines: true }),
    )
  })

  it('respects the chat guidelines toggle when disabled', async () => {
    const sendChat = vi.spyOn(chatApi, 'sendChat').mockResolvedValue({
      session: {
        id: 'session_1',
        title: 'Lake city',
        folder_id: null,
        workspace_id: 'workspace_1',
        created_at: '2026-05-20T12:00:00Z',
        updated_at: '2026-05-20T12:05:00Z',
      },
      user_message: {
        id: 'message_user',
        session_id: 'session_1',
        role: 'user',
        content: 'Question',
        metadata: { turn_kind: 'chat_user' },
        created_at: '2026-05-20T12:00:00Z',
      },
      assistant_message: {
        id: 'message_assistant',
        session_id: 'session_1',
        role: 'assistant',
        content: 'Answer',
        metadata: { turn_kind: 'assistant' },
        created_at: '2026-05-20T12:01:00Z',
      },
      answer: 'Answer',
      sources: [],
      trace_id: 'trace_1',
    })

    const store = useChatStore()
    store.selectedWorkspaceId = 'workspace_1'
    store.selectedChatProfileId = 'profile_1'
    store.applyGuidelinesChat = false
    await store.submitMessage('Question')

    expect(sendChat).toHaveBeenCalledWith(
      expect.objectContaining({ apply_guidelines: false }),
    )
  })
})
