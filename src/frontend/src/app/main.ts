import '@mdi/font/css/materialdesignicons.css'
import 'roboto-fontface/css/roboto/roboto-fontface.css'
import 'vuetify/styles'

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import vuetify from './vuetify'

createApp(App).use(createPinia()).use(router).use(vuetify).mount('#app')
