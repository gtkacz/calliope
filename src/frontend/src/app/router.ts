import { createRouter, createWebHistory } from 'vue-router'

import ChatWorkspace from '@/features/chat/components/ChatWorkspace.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', name: 'chat', component: ChatWorkspace }],
})
