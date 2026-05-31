import { describe, expect, it } from 'vitest'

import { appIconAliases } from './icons'

describe('appIconAliases', () => {
  it('includes the copy glyph used by message actions', () => {
    expect(appIconAliases['mdi-content-copy']).toEqual(expect.any(String))
  })
})
