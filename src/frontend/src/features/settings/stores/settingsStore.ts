import { defineStore } from 'pinia'

export type SettingsTab = 'profiles' | 'workspaces' | 'indexing' | 'appearance'

export const useSettingsStore = defineStore('settings', {
  state: () => ({ open: false, tab: 'profiles' as SettingsTab }),
  actions: {
    show(tab: SettingsTab = 'profiles') {
      this.tab = tab
      this.open = true
    },
    close() {
      this.open = false
    },
  },
})
