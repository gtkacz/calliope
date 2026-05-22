import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import { calliopeDark } from './theme'

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'calliopeDark',
    themes: {
      calliopeDark,
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
      menuIcon: 'mdi-chevron-down',
    },
    VCombobox: {
      variant: 'plain',
      density: 'comfortable',
      hideDetails: 'auto',
      color: 'primary',
      menuIcon: 'mdi-chevron-down',
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
