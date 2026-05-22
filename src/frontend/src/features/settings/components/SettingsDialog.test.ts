import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import { useSettingsStore } from '../stores/settingsStore'
import SettingsDialog from './SettingsDialog.vue'

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('SettingsDialog', () => {
  it('renders settings tabs', () => {
    const settings = useSettingsStore()
    settings.show('profiles')

    const wrapper = mount(SettingsDialog)

    expect(wrapper.text()).toContain('LLM Profiles')
    expect(wrapper.text()).toContain('Workspaces')
    expect(wrapper.text()).toContain('Indexing')
  })
})
