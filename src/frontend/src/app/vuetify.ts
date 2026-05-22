import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'calliopeLight',
    themes: {
      calliopeLight: {
        dark: false,
        colors: {
          background: '#f7f8fa',
          surface: '#ffffff',
          primary: '#315c72',
          secondary: '#6b5f4a',
          accent: '#4f6f52',
          error: '#b3261e',
        },
      },
    },
  },
  defaults: {
    VBtn: { rounded: 'sm' },
    VCard: { rounded: 'sm' },
    VTextField: { density: 'compact', variant: 'outlined' },
    VTextarea: { density: 'compact', variant: 'outlined' },
    VSelect: { density: 'compact', variant: 'outlined' },
  },
})
