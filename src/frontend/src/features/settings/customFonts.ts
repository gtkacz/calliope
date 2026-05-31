import type { FontOption } from './displayFonts'

/** Generic CSS fallback families a custom font can declare, as Google Fonts surfaces them. */
export type FontCategory = 'sans-serif' | 'serif' | 'monospace' | 'cursive' | 'display'

/** Which app font slot a custom font is offered in. */
export type FontSlot = 'display' | 'chat'

export interface CustomFont {
  id: string
  family: string
  category: FontCategory
  slot: FontSlot
  importUrl: string
}

export const FONT_CATEGORIES: readonly FontCategory[] = [
  'sans-serif',
  'serif',
  'display',
  'monospace',
  'cursive',
] as const

export const FONT_SLOTS: readonly FontSlot[] = ['display', 'chat'] as const

const GOOGLE_FONTS_HOST = 'fonts.googleapis.com'

/**
 * Extracts a bare stylesheet URL from whatever the user pastes — a full
 * `<link href="…">` tag, an `@import url('…')` / `@import '…'` rule, or a raw
 * URL — and accepts it only when it points at the Google Fonts css endpoint.
 *
 * Returns the normalised URL string, or null if nothing valid was found.
 */
export function parseGoogleFontsImport(raw: string): string | null {
  const trimmed = raw.trim()
  if (trimmed.length === 0) return null

  // First https URL token, stopping at quotes, parens, angle brackets, or whitespace.
  const match = trimmed.match(/https:\/\/[^"')\s>]+/i)
  if (match === null) return null

  try {
    const url = new URL(match[0])
    if (url.hostname !== GOOGLE_FONTS_HOST) return null
    return url.toString()
  } catch {
    return null
  }
}

/** Builds the CSS font-family stack for a custom font: the family plus its generic fallback. */
export function customFontStack(font: Pick<CustomFont, 'family' | 'category'>): string {
  return `'${font.family}', ${font.category}`
}

/** Projects a custom font onto the shared FontOption shape used by the picker grids. */
export function customFontToOption(font: CustomFont): FontOption {
  return {
    id: font.id,
    label: font.family,
    stack: customFontStack(font),
  }
}

/** Derives a stable, readable id from the family name plus a short suffix for uniqueness. */
export function makeCustomFontId(family: string): string {
  const slug = family
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  const suffix = Date.now().toString(36)
  return `custom-${slug || 'font'}-${suffix}`
}
