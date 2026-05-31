import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AssistantTurn from './AssistantTurn.vue'

function mockClipboard() {
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText },
    configurable: true,
  })
  return writeText
}

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('AssistantTurn', () => {
  it('copies the raw assistant markdown to the clipboard', async () => {
    const writeText = mockClipboard()
    const content = '## Answer\n\n**Canon** stays intact.'
    const wrapper = mount(AssistantTurn, {
      props: { role: 'assistant', content },
    })

    await wrapper.get('[aria-label="Copy message"]').trigger('click')

    expect(writeText).toHaveBeenCalledWith(content)
  })
})
