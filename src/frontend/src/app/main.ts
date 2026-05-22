import '@mdi/font/css/materialdesignicons.css'
import '@fontsource-variable/fraunces'
import '@fontsource-variable/geist'
import '@fontsource-variable/geist-mono'
import 'vuetify/dist/vuetify.css'
import '@/styles/base.css'

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import vuetify from './vuetify'

createApp(App).use(createPinia()).use(router).use(vuetify).mount('#app')
