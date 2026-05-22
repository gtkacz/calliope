import { defineStore } from 'pinia'

import {
  DEFAULT_CHAT_FONT_ID,
  DEFAULT_DISPLAY_FONT_ID,
  findChatFont,
  findDisplayFont,
  type FontOption,
} from '../displayFonts'

const DISPLAY_STORAGE_KEY = 'calliope.appearance.displayFont'
const CHAT_STORAGE_KEY = 'calliope.appearance.chatFont'
const DISPLAY_CSS_VAR = '--calliope-font-display'
const CHAT_CSS_VAR = '--calliope-font-chat'

interface AppearanceState {
  displayFontId: string
  chatFontId: string
}

function readStored(key: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  try {
    return window.localStorage.getItem(key) ?? fallback
  } catch {
    return fallback
  }
}

function writeStored(key: string, value: string): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(key, value)
  } catch {
    /* localStorage unavailable — preference becomes session-only */
  }
}

function applyVariable(cssVar: string, stack: string): void {
  if (typeof document === 'undefined') return
  document.documentElement.style.setProperty(cssVar, stack)
}

export const useAppearanceStore = defineStore('appearance', {
  state: (): AppearanceState => ({
    displayFontId: DEFAULT_DISPLAY_FONT_ID,
    chatFontId: DEFAULT_CHAT_FONT_ID,
  }),
  getters: {
    displayFont(state): FontOption {
      return findDisplayFont(state.displayFontId)
    },
    chatFont(state): FontOption {
      return findChatFont(state.chatFontId)
    },
  },
  actions: {
    init() {
      this.setDisplayFont(readStored(DISPLAY_STORAGE_KEY, DEFAULT_DISPLAY_FONT_ID))
      this.setChatFont(readStored(CHAT_STORAGE_KEY, DEFAULT_CHAT_FONT_ID))
    },
    setDisplayFont(id: string) {
      const font = findDisplayFont(id)
      this.displayFontId = font.id
      applyVariable(DISPLAY_CSS_VAR, font.stack)
      writeStored(DISPLAY_STORAGE_KEY, font.id)
    },
    setChatFont(id: string) {
      const font = findChatFont(id)
      this.chatFontId = font.id
      applyVariable(CHAT_CSS_VAR, font.stack)
      writeStored(CHAT_STORAGE_KEY, font.id)
    },
  },
})
