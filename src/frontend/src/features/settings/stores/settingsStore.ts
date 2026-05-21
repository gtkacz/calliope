import { defineStore } from 'pinia'

export const useSettingsStore = defineStore('settings', {
  state: () => ({ open: false, tab: 'profiles' as 'profiles' | 'workspaces' | 'indexing' }),
  actions: {
    show(tab: 'profiles' | 'workspaces' | 'indexing' = 'profiles') {
      this.tab = tab
      this.open = true
    },
    close() {
      this.open = false
    },
  },
})
