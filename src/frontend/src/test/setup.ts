import { config } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// jsdom does not implement ResizeObserver; Vuetify's auto-grow textarea requires it.
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const vuetify = createVuetify({ components, directives })

config.global.plugins = [vuetify]
config.global.stubs = {
  transition: false,
  'transition-group': false,
  // VNavigationDrawer requires a v-app layout context which is not present in unit tests.
  VNavigationDrawer: { template: '<div><slot /></div>' },
}
