import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import MentionMenu from './MentionMenu.vue'

describe('MentionMenu', () => {
  it('shows the full relative path on the right of each result', () => {
    const wrapper = mount(MentionMenu, {
      props: {
        query: '',
        documents: [
          {
            id: 'document_1',
            title: 'Kaelen',
            path: 'characters/protagonists/kaelen.md',
          },
        ],
      },
    })

    expect(wrapper.get('.mention-menu__path').text()).toBe(
      'characters/protagonists/kaelen.md',
    )
  })
})
