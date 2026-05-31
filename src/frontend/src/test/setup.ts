import { config } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import { aliases as mdiAliases, mdi } from 'vuetify/iconsets/mdi-svg'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import { appIconAliases } from '@/app/icons'

// jsdom does not implement ResizeObserver; Vuetify's auto-grow textarea requires it.
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// jsdom does not implement visualViewport; Vuetify's VOverlay location strategy requires it.
Object.defineProperty(window, 'visualViewport', {
  value: { width: 1024, height: 768, offsetLeft: 0, offsetTop: 0, addEventListener: () => {}, removeEventListener: () => {} },
  writable: true,
})

const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
    aliases: { ...mdiAliases, ...appIconAliases },
    sets: { mdi },
  },
})

config.global.plugins = [vuetify]
config.global.stubs = {
  transition: false,
  'transition-group': false,
  // VDialog uses Teleport to a DOM node which jsdom can't render inline; stub to render slot content directly.
  VDialog: { template: '<div><slot /></div>' },
  // VNavigationDrawer requires a v-app layout context which is not present in unit tests.
  VNavigationDrawer: { template: '<div><slot /></div>' },
}
