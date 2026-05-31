import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as chatApi from '../api'
import * as workspaceApi from '@/features/workspaces/api'
import * as profileApi from '@/features/profiles/api'
import ChatWorkspace from './ChatWorkspace.vue'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.spyOn(chatApi, 'listFolders').mockResolvedValue([])
  vi.spyOn(chatApi, 'listSessions').mockResolvedValue([])
  vi.spyOn(workspaceApi, 'listWorkspaces').mockResolvedValue([])
  vi.spyOn(profileApi, 'listProfiles').mockResolvedValue([])
})

describe('chat flow', () => {
  it('shows recoverable empty configuration state', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const wrapper = mount(ChatWorkspace)
    await vi.dynamicImportSettled()

    expect(wrapper.text()).toContain('Create or select a workspace')
    expect(
      warn.mock.calls.some((call) =>
        call.some(
          (entry) =>
            typeof entry === 'string' &&
            entry.includes('Could not find aliased icon'),
        ),
      ),
    ).toBe(false)
  })
})
