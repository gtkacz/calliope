<script setup lang="ts">
import { useAppearanceStore } from '../stores/appearanceStore'
import { CHAT_FONTS, DISPLAY_FONTS, type FontOption } from '../displayFonts'

const appearance = useAppearanceStore()

interface FontSection {
  title: string
  hint: string
  ariaLabel: string
  options: readonly FontOption[]
  activeId: () => string
  select: (id: string) => void
}

const sections: FontSection[] = [
  {
    title: 'Display font',
    hint: 'Used for headlines, workspace titles, and editorial accents across the studio.',
    ariaLabel: 'Display font',
    options: DISPLAY_FONTS,
    activeId: () => appearance.displayFontId,
    select: (id) => appearance.setDisplayFont(id),
  },
  {
    title: 'Chat font',
    hint: 'Used for the prose inside chat messages — your turns and Calliope’s replies.',
    ariaLabel: 'Chat font',
    options: CHAT_FONTS,
    activeId: () => appearance.chatFontId,
    select: (id) => appearance.setChatFont(id),
  },
]
</script>

<template>
  <div class="appearance-panel">
    <section
      v-for="section in sections"
      :key="section.title"
      class="panel-form font-section"
    >
      <header class="panel-form__head">
        <h3 class="panel-form__title">{{ section.title }}</h3>
        <p class="panel-field__hint">{{ section.hint }}</p>
      </header>

      <div class="font-grid" role="radiogroup" :aria-label="section.ariaLabel">
        <button
          v-for="font in section.options"
          :key="font.id"
          type="button"
          role="radio"
          :aria-checked="font.id === section.activeId()"
          class="font-option__button"
          :class="{ 'is-active': font.id === section.activeId() }"
          @click="section.select(font.id)"
        >
          <span class="font-option__sample" :style="{ fontFamily: font.stack }">
            Calliope
          </span>
          <span class="font-option__label">{{ font.label }}</span>
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.appearance-panel {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.font-section {
  gap: 1.25rem;
}

.font-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.75rem;
}

.font-option__button {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 1.1rem 1rem 0.9rem;
  background: transparent;
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-md);
  color: var(--calliope-paper);
  cursor: pointer;
  text-align: left;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    transform var(--calliope-duration-fast) var(--calliope-ease-out);
}

.font-option__button:hover {
  background: var(--calliope-overlay-hover);
  border-color: var(--calliope-border-strong);
}

.font-option__button:focus-visible {
  outline: 2px solid var(--calliope-bronze);
  outline-offset: 2px;
}

.font-option__button.is-active {
  border-color: var(--calliope-bronze);
  background: var(--calliope-bronze-veil);
}

.font-option__button.is-active::after {
  content: '';
  position: absolute;
  top: 0.65rem;
  right: 0.75rem;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--calliope-bronze);
  box-shadow: 0 0 0 4px var(--calliope-bronze-veil);
}

.font-option__sample {
  font-size: 1.65rem;
  line-height: 1.05;
  letter-spacing: -0.012em;
  color: var(--calliope-paper);
}

.font-option__label {
  font-family: var(--calliope-font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--calliope-paper-dim);
}

.font-option__button.is-active .font-option__label {
  color: var(--calliope-paper-muted);
}
</style>
