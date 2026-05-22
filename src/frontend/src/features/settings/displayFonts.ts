export interface FontOption {
  id: string
  label: string
  stack: string
}

export const DEFAULT_DISPLAY_FONT_ID = 'fraunces'
export const DEFAULT_CHAT_FONT_ID = 'geist'

export const DISPLAY_FONTS: readonly FontOption[] = [
  {
    id: DEFAULT_DISPLAY_FONT_ID,
    label: 'Fraunces (default)',
    stack: "'Fraunces Variable', 'Fraunces', Georgia, 'Times New Roman', serif",
  },
  { id: 'amarante', label: 'Amarante', stack: "'Amarante', serif" },
  { id: 'metamorphous', label: 'Metamorphous', stack: "'Metamorphous', serif" },
  {
    id: 'macondo-swash-caps',
    label: 'Macondo Swash Caps',
    stack: "'Macondo Swash Caps', serif",
  },
  {
    id: 'cormorant-unicase',
    label: 'Cormorant Unicase',
    stack: "'Cormorant Unicase', serif",
  },
  { id: 'pirata-one', label: 'Pirata One', stack: "'Pirata One', serif" },
  { id: 'grenze-gotisch', label: 'Grenze Gotisch', stack: "'Grenze Gotisch', serif" },
  { id: 'germania-one', label: 'Germania One', stack: "'Germania One', serif" },
  { id: 'astloch', label: 'Astloch', stack: "'Astloch', serif" },
  { id: 'almendra-sc', label: 'Almendra SC', stack: "'Almendra SC', serif" },
] as const

export const CHAT_FONTS: readonly FontOption[] = [
  {
    id: DEFAULT_CHAT_FONT_ID,
    label: 'Geist (default)',
    stack: "'Geist Variable', 'Geist', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif",
  },
  { id: 'texturina', label: 'Texturina', stack: "'Texturina', serif" },
  { id: 'nova-cut', label: 'Nova Cut', stack: "'Nova Cut', serif" },
  { id: 'jim-nightshade', label: 'Jim Nightshade', stack: "'Jim Nightshade', cursive" },
  { id: 'almendra', label: 'Almendra', stack: "'Almendra', serif" },
  { id: 'quintessential', label: 'Quintessential', stack: "'Quintessential', serif" },
  { id: 'fondamento', label: 'Fondamento', stack: "'Fondamento', cursive" },
  { id: 'cormorant', label: 'Cormorant', stack: "'Cormorant', serif" },
] as const

export function findDisplayFont(id: string | null | undefined): FontOption {
  if (!id) return DISPLAY_FONTS[0]
  return DISPLAY_FONTS.find((font) => font.id === id) ?? DISPLAY_FONTS[0]
}

export function findChatFont(id: string | null | undefined): FontOption {
  if (!id) return CHAT_FONTS[0]
  return CHAT_FONTS.find((font) => font.id === id) ?? CHAT_FONTS[0]
}
