/**
 * Single source of truth for all preset palettes and theming types.
 * Permitted importers: theme.ts (Vuetify ThemeDefinitions), appearanceStore (CSS var injection),
 * and the settings AppearancePanel (to read PRESETS/PresetId for the UI).
 * All other components consume --calliope-* CSS vars only and must not import this directly.
 */

export type PresetId = 'scriptorium' | 'twilight' | 'vellum-noir' | 'classic'
export type TypeScale = 'compact' | 'cozy' | 'comfortable'
export type Density = 'compact' | 'default' | 'airy'

export interface PresetPalette {
  name: string
  default?: true
  background: string
  surface: string
  surfaceRaised: string
  surfaceTop: string
  text: string
  textMuted: string
  textDim: string
  border: string
  accent: string
  accentDeep: string
  secondary: string
  error: string
  success: string
  warning: string
}

export const PRESETS: Record<PresetId, PresetPalette> = {
  scriptorium: {
    name: 'Gilded Scriptorium',
    default: true,
    background: '#09080A',
    surface: '#141018',
    surfaceRaised: '#1E1826',
    surfaceTop: '#2A2235',
    text: '#F2E8D3',
    textMuted: 'rgba(242,232,211,0.70)',
    textDim: 'rgba(242,232,211,0.55)',
    border: 'rgba(242,232,211,0.11)',
    accent: '#D4A853',
    accentDeep: '#B8893A',
    secondary: '#5A8A7E',
    error: '#C96355',
    success: '#6B9E7A',
    warning: '#C9913A',
  },
  twilight: {
    name: 'Arcane Twilight',
    background: '#0A0912',
    surface: '#100E1C',
    surfaceRaised: '#18162A',
    surfaceTop: '#201E36',
    text: '#EDE8F5',
    textMuted: 'rgba(237,232,245,0.66)',
    textDim: 'rgba(237,232,245,0.52)',
    border: 'rgba(237,232,245,0.11)',
    accent: '#D4AF6A',
    accentDeep: '#B8974E',
    secondary: '#7AB3C4',
    error: '#D97B6B',
    success: '#7A9B7E',
    warning: '#D9A86B',
  },
  'vellum-noir': {
    name: 'Ink & Vellum Noir',
    background: '#0A0A0B',
    surface: '#111114',
    surfaceRaised: '#18181C',
    surfaceTop: '#1F1F24',
    text: '#F0EDE8',
    textMuted: 'rgba(240,237,232,0.60)',
    textDim: 'rgba(240,237,232,0.50)',
    border: 'rgba(240,237,232,0.10)',
    accent: '#C04C5E',
    accentDeep: '#9B2C3A',
    secondary: '#6B6B7A',
    error: '#C04558',
    success: '#4A8C6A',
    warning: '#B8863A',
  },
  classic: {
    name: 'Classic Studio',
    background: '#0E0C09',
    surface: '#18140E',
    surfaceRaised: '#2A2317',
    surfaceTop: '#342B1C',
    text: '#EFE7D6',
    textMuted: 'rgba(239,231,214,0.66)',
    textDim: 'rgba(239,231,214,0.56)',
    border: 'rgba(239,231,214,0.14)',
    accent: '#C9A36A',
    accentDeep: '#B5905A',
    secondary: '#5F8693',
    error: '#D97B6B',
    success: '#7A9B7E',
    warning: '#D9A86B',
  },
} as const

export const DEFAULT_PRESET_ID: PresetId = 'scriptorium'

/** px values that drive --calliope-root-size per type scale setting */
export const TYPE_SCALE_ROOT_PX: Record<TypeScale, number> = {
  compact: 15,
  cozy: 16,
  comfortable: 17,
}

/** multipliers applied to spacing scale tokens per density setting */
export const DENSITY_MULT: Record<Density, number> = {
  compact: 0.85,
  default: 1,
  airy: 1.18,
}
