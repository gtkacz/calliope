import { createVuetify } from 'vuetify'

export default createVuetify({
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
