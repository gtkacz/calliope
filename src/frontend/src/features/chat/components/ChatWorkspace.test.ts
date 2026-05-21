import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as chatApi from '../api'
import ChatWorkspace from './ChatWorkspace.vue'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.spyOn(chatApi, 'listFolders').mockResolvedValue([])
  vi.spyOn(chatApi, 'listSessions').mockResolvedValue([])
})

describe('ChatWorkspace', () => {
  it('renders the conversation drawer and composer controls', async () => {
    const wrapper = mount(ChatWorkspace, { global: { stubs: ['v-icon'] } })
    await vi.dynamicImportSettled()

    expect(wrapper.text()).toContain('New conversation')
    expect(wrapper.text()).toContain('Chat')
    expect(wrapper.text()).toContain('Search')
    expect(wrapper.find('textarea').exists()).toBe(true)
  })
})
