import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import MessageBubble from './MessageBubble.vue'

function mockClipboard() {
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText },
    configurable: true,
  })
  return writeText
}

describe('MessageBubble', () => {
  it('copies the raw user message to the clipboard', async () => {
    const writeText = mockClipboard()
    const content = '# User note\n\n- Keep the markdown.'
    const wrapper = mount(MessageBubble, { props: { content } })

    await wrapper.get('[aria-label="Copy message"]').trigger('click')

    expect(writeText).toHaveBeenCalledWith(content)
  })

  it('shows a copied toast after clipboard write succeeds', async () => {
    mockClipboard()
    const wrapper = mount(MessageBubble, { props: { content: 'Plain text' } })

    await wrapper.get('[aria-label="Copy message"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Copied to clipboard')
  })
})
