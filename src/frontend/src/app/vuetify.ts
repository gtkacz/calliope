import { createVuetify } from 'vuetify'
import { aliases as mdiAliases, mdi } from 'vuetify/iconsets/mdi-svg'

import { appIconAliases } from './icons'
import {
  calliopeScriptorium,
  calliopeTwilight,
  calliopeVellumNoir,
  calliopeClassic,
} from './theme'

// Components and directives are auto-imported per-use by vite-plugin-vuetify
// (configured in vite.config.ts), so only what the app references is bundled.
const vuetify = createVuetify({
  icons: {
    defaultSet: 'mdi',
    // mdiAliases supplies Vuetify's internal icons (dropdown, clear, close…);
    // appIconAliases adds the app's own glyphs as tree-shaken SVG paths.
    aliases: { ...mdiAliases, ...appIconAliases },
    sets: { mdi },
  },
  theme: {
    defaultTheme: 'calliopeScriptorium',
    themes: {
      calliopeScriptorium,
      calliopeTwilight,
      calliopeVellumNoir,
      calliopeClassic,
    },
  },
  defaults: {
    global: {
      ripple: false,
    },
    VBtn: {
      variant: 'flat',
      rounded: 'lg',
      color: 'primary',
      flat: true,
      style: 'text-transform: none; letter-spacing: 0;',
    },
    VCard: {
      variant: 'flat',
      rounded: 'md',
      color: 'surface',
    },
    VTextField: {
      variant: 'plain',
      density: 'comfortable',
      hideDetails: 'auto',
      color: 'primary',
    },
    VTextarea: {
      variant: 'plain',
      density: 'comfortable',
      hideDetails: 'auto',
      color: 'primary',
    },
    VSelect: {
      variant: 'plain',
      density: 'comfortable',
      hideDetails: 'auto',
      color: 'primary',
      menuIcon: '$mdi-chevron-down',
    },
    VCombobox: {
      variant: 'plain',
      density: 'comfortable',
      hideDetails: 'auto',
      color: 'primary',
      menuIcon: '$mdi-chevron-down',
    },
    VAutocomplete: {
      variant: 'plain',
      density: 'comfortable',
      hideDetails: 'auto',
      color: 'primary',
    },
    VList: {
      density: 'comfortable',
      bgColor: 'transparent',
    },
    VListItem: {
      rounded: 'md',
    },
    VDialog: {
      rounded: 'lg',
      scrollStrategy: 'block',
    },
    VAlert: {
      variant: 'tonal',
      rounded: 'md',
    },
    VChip: {
      variant: 'tonal',
      rounded: 'pill',
      size: 'small',
    },
    VTabs: {
      sliderColor: 'primary',
      density: 'comfortable',
    },
    VProgressLinear: {
      color: 'primary',
      rounded: true,
      bgOpacity: 0.08,
    },
    VTooltip: {
      contentClass: 'calliope-tooltip',
      transition: 'fade-transition',
    },
  },
})

/** Swap the Vuetify active theme by name. Called by the appearance store when the user changes palette. */
export function setActiveVuetifyTheme(name: string): void {
  vuetify.theme.change(name)
}

export default vuetify
