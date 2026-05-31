import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import { useChatStore } from '../stores/chatStore'
import ComposerBar from './ComposerBar.vue'

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('ComposerBar', () => {
  it('shows the full relative path on selected file citations', () => {
    const chat = useChatStore()
    chat.mentionDocuments = [
      {
        id: 'document_1',
        title: 'Kaelen',
        path: 'characters/protagonists/kaelen.md',
      },
    ]
    chat.mentionWorkspaceId = 'workspace_1'
    chat.citedDocumentIds = ['document_1']

    const wrapper = mount(ComposerBar, {
      props: {
        mode: 'chat',
        policy: 'strict_canon',
        selectedWorkspaceId: 'workspace_1',
        selectedChatProfileId: 'profile_1',
        workspaces: [],
        profiles: [],
        pending: false,
        disabled: false,
      },
    })

    expect(wrapper.get('.composer__citation').text()).toContain(
      'characters/protagonists/kaelen.md',
    )
  })
})
