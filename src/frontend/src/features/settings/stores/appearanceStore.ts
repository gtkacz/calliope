import { defineStore } from 'pinia'

import {
  DEFAULT_CHAT_FONT_ID,
  DEFAULT_DISPLAY_FONT_ID,
  findChatFont,
  findDisplayFont,
  type FontOption,
} from '../displayFonts'
import { ensureFontsLoaded } from '@/composables/useDecorativeFonts'
import {
  PRESETS,
  TYPE_SCALE_ROOT_PX,
  DENSITY_MULT,
  DEFAULT_PRESET_ID,
  type PresetId,
  type TypeScale,
  type Density,
} from '@/app/tokens'

const DISPLAY_STORAGE_KEY = 'calliope.appearance.displayFont'
const CHAT_STORAGE_KEY = 'calliope.appearance.chatFont'
const PALETTE_STORAGE_KEY = 'calliope.appearance.palette'
const ACCENT_STORAGE_KEY = 'calliope.appearance.accentHex'
const TYPE_SCALE_STORAGE_KEY = 'calliope.appearance.typeScale'
const DENSITY_STORAGE_KEY = 'calliope.appearance.density'

const DISPLAY_CSS_VAR = '--calliope-font-display'
const CHAT_CSS_VAR = '--calliope-font-chat'

interface AppearanceState {
  displayFontId: string
  chatFontId: string
  paletteId: PresetId
  accentHex: string | null
  typeScale: TypeScale
  density: Density
}

function readStored(key: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  try {
    return window.localStorage.getItem(key) ?? fallback
  } catch {
    return fallback
  }
}

function writeStored(key: string, value: string): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(key, value)
  } catch {
    /* localStorage unavailable — preference becomes session-only */
  }
}

function removeStored(key: string): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(key)
  } catch {
    /* no-op */
  }
}

function applyVariable(cssVar: string, value: string): void {
  if (typeof document === 'undefined') return
  document.documentElement.style.setProperty(cssVar, value)
}

/**
 * Darkens a hex colour by reducing its HSL lightness by the given delta.
 * Used to derive accentDeep from a custom accent without importing a colour library.
 */
function darkenHex(hex: string, deltaL: number): string {
  if (!/^#[0-9a-f]{6}$/i.test(hex)) { return hex }
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)

  const rn = r / 255
  const gn = g / 255
  const bn = b / 255

  const max = Math.max(rn, gn, bn)
  const min = Math.min(rn, gn, bn)
  let h = 0
  let s = 0
  let l = (max + min) / 2

  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case rn:
        h = ((gn - bn) / d + (gn < bn ? 6 : 0)) / 6
        break
      case gn:
        h = ((bn - rn) / d + 2) / 6
        break
      default:
        h = ((rn - gn) / d + 4) / 6
    }
  }

  l = Math.min(0.75, Math.max(0.20, l - deltaL / 100))

  function hue2rgb(p: number, q: number, t: number): number {
    let tt = t
    if (tt < 0) tt += 1
    if (tt > 1) tt -= 1
    if (tt < 1 / 6) return p + (q - p) * 6 * tt
    if (tt < 1 / 2) return q
    if (tt < 2 / 3) return p + (q - p) * (2 / 3 - tt) * 6
    return p
  }

  let r2: number
  let g2: number
  let b2: number

  if (s === 0) {
    r2 = g2 = b2 = l
  } else {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s
    const p = 2 * l - q
    r2 = hue2rgb(p, q, h + 1 / 3)
    g2 = hue2rgb(p, q, h)
    b2 = hue2rgb(p, q, h - 1 / 3)
  }

  const toHex = (x: number) => Math.round(x * 255).toString(16).padStart(2, '0')
  return `#${toHex(r2)}${toHex(g2)}${toHex(b2)}`
}

export const useAppearanceStore = defineStore('appearance', {
  state: (): AppearanceState => ({
    displayFontId: DEFAULT_DISPLAY_FONT_ID,
    chatFontId: DEFAULT_CHAT_FONT_ID,
    paletteId: DEFAULT_PRESET_ID,
    accentHex: null,
    typeScale: 'cozy',
    density: 'default',
  }),
  getters: {
    displayFont(state): FontOption {
      return findDisplayFont(state.displayFontId)
    },
    chatFont(state): FontOption {
      return findChatFont(state.chatFontId)
    },
  },
  actions: {
    init() {
      const storedPalette = readStored(PALETTE_STORAGE_KEY, DEFAULT_PRESET_ID)
      this.paletteId = (storedPalette in PRESETS ? storedPalette : DEFAULT_PRESET_ID) as PresetId

      this.accentHex = readStored(ACCENT_STORAGE_KEY, '') || null

      const storedScale = readStored(TYPE_SCALE_STORAGE_KEY, 'cozy')
      this.typeScale = (['compact', 'cozy', 'comfortable'] as const).includes(storedScale as TypeScale)
        ? (storedScale as TypeScale)
        : 'cozy'

      const storedDensity = readStored(DENSITY_STORAGE_KEY, 'default')
      this.density = (['compact', 'default', 'airy'] as const).includes(storedDensity as Density)
        ? (storedDensity as Density)
        : 'default'

      // Apply palette + type scale + density before paint so there is no FOUC.
      this._apply()

      const displayId = readStored(DISPLAY_STORAGE_KEY, DEFAULT_DISPLAY_FONT_ID)
      const chatId = readStored(CHAT_STORAGE_KEY, DEFAULT_CHAT_FONT_ID)

      this.setDisplayFont(displayId)
      this.setChatFont(chatId)

      // Preload any saved decorative fonts that are not bundled via fontsource.
      const decorativeIds = [displayId, chatId].filter(
        (id) => id !== DEFAULT_DISPLAY_FONT_ID && id !== DEFAULT_CHAT_FONT_ID,
      )
      if (decorativeIds.length > 0) {
        ensureFontsLoaded(decorativeIds)
      }
    },

    setDisplayFont(id: string) {
      const font = findDisplayFont(id)
      this.displayFontId = font.id
      applyVariable(DISPLAY_CSS_VAR, font.stack)
      writeStored(DISPLAY_STORAGE_KEY, font.id)
    },

    setChatFont(id: string) {
      const font = findChatFont(id)
      this.chatFontId = font.id
      applyVariable(CHAT_CSS_VAR, font.stack)
      writeStored(CHAT_STORAGE_KEY, font.id)
    },

    setPalette(id: PresetId) {
      this.paletteId = id
      writeStored(PALETTE_STORAGE_KEY, id)
      this._apply()
    },

    setAccent(hex: string | null) {
      this.accentHex = hex
      if (hex) {
        writeStored(ACCENT_STORAGE_KEY, hex)
      } else {
        removeStored(ACCENT_STORAGE_KEY)
      }
      this._apply()
    },

    setTypeScale(scale: TypeScale) {
      this.typeScale = scale
      writeStored(TYPE_SCALE_STORAGE_KEY, scale)
      this._apply()
    },

    setDensity(density: Density) {
      this.density = density
      writeStored(DENSITY_STORAGE_KEY, density)
      this._apply()
    },

    /** Writes all --calliope-* CSS vars and swaps the Vuetify theme. */
    _apply() {
      if (typeof document === 'undefined') return

      const palette = PRESETS[this.paletteId] ?? PRESETS[DEFAULT_PRESET_ID]
      const accent = this.accentHex ?? palette.accent
      const accentDeep = this.accentHex ? darkenHex(this.accentHex, 12) : palette.accentDeep

      // Derive rgba variants of the active accent for glow/veil tokens.
      const accentRgbMatch = accent.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i)
      const accentRgb = accentRgbMatch
        ? `${parseInt(accentRgbMatch[1], 16)}, ${parseInt(accentRgbMatch[2], 16)}, ${parseInt(accentRgbMatch[3], 16)}`
        : '212, 168, 83'

      // Derive rgba variants of the palette error colour for warm-error tokens.
      const errorRgbMatch = palette.error.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i)
      const errorRgb = errorRgbMatch
        ? `${parseInt(errorRgbMatch[1], 16)}, ${parseInt(errorRgbMatch[2], 16)}, ${parseInt(errorRgbMatch[3], 16)}`
        : '201, 99, 85'

      const vars: Record<string, string> = {
        // Palette surface tokens
        '--calliope-ink': palette.background,
        '--calliope-ink-soft': palette.surface,
        '--calliope-ink-raised': palette.surfaceRaised,
        '--calliope-ink-top': palette.surfaceTop,
        '--calliope-paper': palette.text,
        '--calliope-paper-muted': palette.textMuted,
        '--calliope-paper-dim': palette.textDim,
        '--calliope-paper-faint': palette.border,
        // Accent slot
        '--calliope-bronze': accent,
        '--calliope-bronze-deep': accentDeep,
        '--calliope-bronze-glow': `rgba(${accentRgb}, 0.22)`,
        '--calliope-bronze-veil': `rgba(${accentRgb}, 0.10)`,
        // Semantic colour tokens
        '--calliope-dim-teal': palette.secondary,
        '--calliope-warm-error': palette.error,
        '--calliope-warm-error-soft': `rgba(${errorRgb}, 0.36)`,
        '--calliope-warm-error-veil': `rgba(${errorRgb}, 0.08)`,
        // Borders (derived from palette border base)
        '--calliope-border': palette.border,
        '--calliope-border-strong': palette.border.replace(/[\d.]+\)$/, '0.22)'),
        '--calliope-overlay-hover': palette.textDim.replace(/[\d.]+\)$/, '0.06)'),
        '--calliope-overlay-active': `rgba(${accentRgb}, 0.18)`,
        // Gilt hairline gradient stop colour for manuscript rule decorations
        '--calliope-rule': accent,
        // Type scale
        '--calliope-root-size': `${TYPE_SCALE_ROOT_PX[this.typeScale]}px`,
        // Density multiplier
        '--calliope-density-mult': String(DENSITY_MULT[this.density]),
      }

      for (const [prop, value] of Object.entries(vars)) {
        document.documentElement.style.setProperty(prop, value)
      }

      // Swap Vuetify's active theme so Vuetify-internal components (ripples,
      // overlays, etc.) also reflect the correct palette.
      const vuetifyThemeMap: Record<PresetId, string> = {
        scriptorium: 'calliopeScriptorium',
        twilight: 'calliopeTwilight',
        'vellum-noir': 'calliopeVellumNoir',
        classic: 'calliopeClassic',
      }
      // Dynamic import avoids a circular dependency: store → vuetify → theme → tokens → store.
      // The try/catch ensures a no-op in test/SSR environments where the module is absent.
      import('@/app/vuetify').then((mod) => {
        mod.setActiveVuetifyTheme(vuetifyThemeMap[this.paletteId])
      }).catch(() => {
        // Vuetify module not reachable — CSS vars alone drive the visual output.
      })
    },
  },
})
