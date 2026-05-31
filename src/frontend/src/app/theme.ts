import type { ThemeDefinition } from 'vuetify'

import { PRESETS } from './tokens'

/** Standard sRGB relative luminance from a #rrggbb hex string. */
function relativeLuminance(hex: string): number {
  const parse = (slice: string) => {
    const c = parseInt(slice, 16) / 255
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
  }
  const r = parse(hex.slice(1, 3))
  const g = parse(hex.slice(3, 5))
  const b = parse(hex.slice(5, 7))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function makeTheme(id: keyof typeof PRESETS): ThemeDefinition {
  const p = PRESETS[id]
  // Dark/saturated accents (luminance < 0.18) need the light text colour on top;
  // bright accents use the dark background so the label stays legible.
  const onPrimary = relativeLuminance(p.accent) < 0.18 ? p.text : p.background
  return {
    dark: true,
    colors: {
      background: p.background,
      surface: p.surface,
      'surface-bright': p.surfaceRaised,
      'surface-light': p.surfaceTop,
      'surface-variant': p.surfaceRaised,
      'on-surface': p.text,
      'on-background': p.text,
      'on-surface-variant': p.textMuted,
      primary: p.accent,
      'primary-darken-1': p.accentDeep,
      'on-primary': onPrimary,
      secondary: p.secondary,
      'secondary-darken-1': p.secondary,
      'on-secondary': p.background,
      accent: p.accent,
      error: p.error,
      'on-error': p.background,
      info: p.secondary,
      success: p.success,
      warning: p.warning,
    },
    variables: {
      'border-color': '239, 231, 214',
      'border-opacity': 0.12,
      'high-emphasis-opacity': 0.92,
      'medium-emphasis-opacity': 0.66,
      'disabled-opacity': 0.32,
      'hover-opacity': 0.04,
      'focus-opacity': 0.10,
      'selected-opacity': 0.12,
      'activated-opacity': 0.14,
      'pressed-opacity': 0.18,
      'dragged-opacity': 0.10,
      'theme-kbd': p.surfaceRaised,
      'theme-on-kbd': p.text,
      'theme-code': p.surface,
      'theme-on-code': p.text,
    },
  }
}

export const calliopeScriptorium: ThemeDefinition = makeTheme('scriptorium')
export const calliopeTwilight: ThemeDefinition = makeTheme('twilight')
export const calliopeVellumNoir: ThemeDefinition = makeTheme('vellum-noir')
export const calliopeClassic: ThemeDefinition = makeTheme('classic')

/** Kept for backwards compatibility — components/tests referencing calliopeDark still compile. */
export const calliopeDark: ThemeDefinition = calliopeScriptorium
