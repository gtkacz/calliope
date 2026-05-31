import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import TypingIndicator from './TypingIndicator.vue'

describe('TypingIndicator', () => {
  it('renders loading dots inline with the Calliope wordmark', () => {
    const wrapper = mount(TypingIndicator)

    const role = wrapper.get('.typing-indicator__role')
    const dots = role.get('.typing-indicator__dots')

    expect(dots.findAll('.typing-indicator__dot')).toHaveLength(3)
  })
})
