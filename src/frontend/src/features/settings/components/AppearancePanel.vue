<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useAppearanceStore } from '../stores/appearanceStore'
import { CHAT_FONTS, DEFAULT_CHAT_FONT_ID, DEFAULT_DISPLAY_FONT_ID, DISPLAY_FONTS, type FontOption } from '../displayFonts'
import { PRESETS, type PresetId, type TypeScale, type Density } from '@/app/tokens'
import { ensureFontsLoaded } from '@/composables/useDecorativeFonts'

const appearance = useAppearanceStore()

// ─── Palette presets ──────────────────────────────────────────────────────────

const presetIds = Object.keys(PRESETS) as PresetId[]

// ─── Accent swatches ─────────────────────────────────────────────────────────

// A curated set of accent hues that complement the editorial palettes.
// These are fed through CSS vars at runtime — the actual hex values live in the
// store/tokens layer and never appear in components; but we need to seed the
// swatch row with the per-preset accent values so it stays in sync.
const accentSwatches = computed(() =>
  presetIds.map((id) => ({ id, hex: PRESETS[id].accent })),
)

// Controlled by a native <input type="color"> for arbitrary picks.
const colorPickerRef = ref<HTMLInputElement | null>(null)

function openColorPicker() {
  colorPickerRef.value?.click()
}

function onColorInput(event: Event) {
  const target = event.target as HTMLInputElement
  appearance.setAccent(target.value)
}

// ─── Type scale ───────────────────────────────────────────────────────────────

interface ScaleOption {
  value: TypeScale
  label: string
}

const typeScaleOptions: ScaleOption[] = [
  { value: 'compact', label: 'Compact' },
  { value: 'cozy', label: 'Cozy' },
  { value: 'comfortable', label: 'Comfortable' },
]

// ─── Density ─────────────────────────────────────────────────────────────────

interface DensityOption {
  value: Density
  label: string
}

const densityOptions: DensityOption[] = [
  { value: 'compact', label: 'Compact' },
  { value: 'default', label: 'Default' },
  { value: 'airy', label: 'Airy' },
]

// ─── Font sections ────────────────────────────────────────────────────────────

interface FontSection {
  title: string
  hint: string
  ariaLabel: string
  options: readonly FontOption[]
  activeId: () => string
  select: (id: string) => void
}

const fontSections: FontSection[] = [
  {
    title: 'Display font',
    hint: 'Used for headlines, workspace titles, and editorial accents across the studio.',
    ariaLabel: 'Display font',
    options: DISPLAY_FONTS,
    activeId: () => appearance.displayFontId,
    select: (id) => {
      ensureFontsLoaded([id])
      appearance.setDisplayFont(id)
    },
  },
  {
    title: 'Chat font',
    hint: 'Used for the prose inside chat messages — your turns and Calliope’s replies.',
    ariaLabel: 'Chat font',
    options: CHAT_FONTS,
    activeId: () => appearance.chatFontId,
    select: (id) => {
      ensureFontsLoaded([id])
      appearance.setChatFont(id)
    },
  },
]

// ─── Font loading guard ───────────────────────────────────────────────────────

// Tracks whether document.fonts has reported ready so the font grid can
// fade unloaded options gracefully until the browser confirms they are available.
const fontsReady = ref(false)

function isFontLoaded(stack: string): boolean {
  if (!fontsReady.value) {
    return false
  }
  // Extract the first quoted family name from the stack string.
  const match = stack.match(/['"]([^'"]+)['"]/)
  if (!match) {
    return true
  }
  return document.fonts.check(`1em ${match[1]}`)
}

onMounted(async () => {
  // Ensure any decorative fonts already persisted by the store are loaded so
  // the font pickers show correct previews on open.
  const decorativeIds = [appearance.displayFontId, appearance.chatFontId].filter(
    (id) => id !== DEFAULT_DISPLAY_FONT_ID && id !== DEFAULT_CHAT_FONT_ID,
  )
  if (decorativeIds.length > 0) {
    await ensureFontsLoaded(decorativeIds)
  } else {
    await document.fonts.ready
  }
  fontsReady.value = true
})
</script>

<template>
  <div class="appearance-panel">

    <!-- ── 1. Studio Palette ──────────────────────────────────────────── -->
    <section class="panel-form">
      <header class="panel-form__head">
        <span class="calliope-eyebrow">Studio</span>
        <h3 class="panel-form__title calliope-serif">Studio palette</h3>
        <p class="panel-field__hint">Sets the overall ink, paper, and surface colours across the workspace.</p>
      </header>

      <div class="palette-gallery" role="radiogroup" aria-label="Studio palette">
        <button
          v-for="id in presetIds"
          :key="id"
          type="button"
          role="radio"
          :aria-checked="appearance.paletteId === id"
          class="palette-card"
          :class="{ 'is-active': appearance.paletteId === id }"
          @click="appearance.setPalette(id)"
        >
          <!-- 3-swatch strip: ink / paper / accent -->
          <span class="palette-swatches" aria-hidden="true">
            <span
              class="palette-swatch"
              :style="{ background: PRESETS[id].background }"
            />
            <span
              class="palette-swatch"
              :style="{ background: PRESETS[id].text }"
            />
            <span
              class="palette-swatch"
              :style="{ background: PRESETS[id].accent }"
            />
          </span>
          <span class="palette-card__name">{{ PRESETS[id].name }}</span>
          <span
            v-if="appearance.paletteId === id"
            class="palette-card__active-dot"
            aria-hidden="true"
          />
        </button>
      </div>
    </section>

    <!-- ── 2. Accent Colour ───────────────────────────────────────────── -->
    <section class="panel-form">
      <header class="panel-form__head">
        <span class="calliope-eyebrow">Accent</span>
        <h3 class="panel-form__title calliope-serif">Accent colour</h3>
        <p class="panel-field__hint">Overrides the preset accent used for borders, icons, and gilt highlights.</p>
      </header>

      <div class="accent-row" role="radiogroup" aria-label="Accent colour">
        <!-- Per-preset swatches as quick picks -->
        <button
          v-for="swatch in accentSwatches"
          :key="swatch.id"
          type="button"
          role="radio"
          :aria-checked="!appearance.accentHex && appearance.paletteId === swatch.id"
          :aria-label="`${PRESETS[swatch.id].name} accent`"
          class="accent-swatch-btn"
          :class="{ 'is-active': !appearance.accentHex && appearance.paletteId === swatch.id }"
          :style="{ '--swatch-color': swatch.hex }"
          @click="appearance.setAccent(null); appearance.setPalette(swatch.id)"
        />

        <!-- Freeform colour picker trigger -->
        <button
          type="button"
          class="accent-swatch-btn accent-swatch-btn--custom"
          :class="{ 'is-active': !!appearance.accentHex }"
          aria-label="Custom accent colour"
          :style="appearance.accentHex ? { '--swatch-color': appearance.accentHex } : {}"
          @click="openColorPicker"
        >
          <v-icon icon="mdi-eyedropper-variant" size="14" />
        </button>

        <!-- Native color input — visually hidden, triggered by the button above -->
        <input
          ref="colorPickerRef"
          type="color"
          class="accent-color-input"
          :value="appearance.accentHex ?? PRESETS[appearance.paletteId].accent"
          aria-hidden="true"
          tabindex="-1"
          @input="onColorInput"
        />

        <!-- Reset to preset default -->
        <button
          v-if="appearance.accentHex"
          type="button"
          class="accent-reset-btn"
          aria-label="Reset to preset accent"
          @click="appearance.setAccent(null)"
        >
          <v-icon icon="mdi-restore" size="13" />
          Reset
        </button>
      </div>
    </section>

    <!-- ── 3. Text Size ───────────────────────────────────────────────── -->
    <section class="panel-form">
      <header class="panel-form__head">
        <span class="calliope-eyebrow">Typography</span>
        <h3 class="panel-form__title calliope-serif">Text size</h3>
        <p class="panel-field__hint">Scales the global rem base, affecting all text and relative measurements.</p>
      </header>

      <div
        class="segmented-control"
        role="radiogroup"
        aria-label="Text size"
      >
        <button
          v-for="opt in typeScaleOptions"
          :key="opt.value"
          type="button"
          role="radio"
          :aria-checked="appearance.typeScale === opt.value"
          class="segmented-control__option"
          :class="{ 'is-active': appearance.typeScale === opt.value }"
          @click="appearance.setTypeScale(opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>
    </section>

    <!-- ── 4. Density ─────────────────────────────────────────────────── -->
    <section class="panel-form">
      <header class="panel-form__head">
        <span class="calliope-eyebrow">Layout</span>
        <h3 class="panel-form__title calliope-serif">Density</h3>
        <p class="panel-field__hint">Adjusts the spacing scale multiplier across panels, sidebars, and the reading column.</p>
      </header>

      <div
        class="segmented-control"
        role="radiogroup"
        aria-label="Layout density"
      >
        <button
          v-for="opt in densityOptions"
          :key="opt.value"
          type="button"
          role="radio"
          :aria-checked="appearance.density === opt.value"
          class="segmented-control__option"
          :class="{ 'is-active': appearance.density === opt.value }"
          @click="appearance.setDensity(opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>
    </section>

    <!-- ── 5. Display font + Chat font ───────────────────────────────── -->
    <section
      v-for="section in fontSections"
      :key="section.title"
      class="panel-form font-section"
    >
      <header class="panel-form__head">
        <span class="calliope-eyebrow">Fonts</span>
        <h3 class="panel-form__title calliope-serif">{{ section.title }}</h3>
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
          :class="{
            'is-active': font.id === section.activeId(),
            'is-loading': !isFontLoaded(font.stack),
          }"
          @click="section.select(font.id)"
        >
          <span class="font-option__sample" :style="{ fontFamily: font.stack }">
            Calliope
          </span>
          <span class="font-option__label">{{ font.label }}</span>
        </button>
      </div>
    </section>

    <!-- ── 6. Live preview well ───────────────────────────────────────── -->
    <section class="panel-form preview-section">
      <header class="panel-form__head">
        <span class="calliope-eyebrow">Preview</span>
        <h3 class="panel-form__title calliope-serif">Live preview</h3>
      </header>

      <div class="preview-well">
        <p class="preview-well__display calliope-display">
          The Gilded Marginalia
        </p>
        <p class="preview-well__body">
          In the monastery's scriptorium, candlelight pooled across vellum
          thick as board, and the monk pressed his reed pen into the first word
          of a world not yet named. Each stroke carried the slight tremor of
          devotion — conviction worn smooth by three decades of daily practice.
          Outside, an autumn storm pressed its grey shoulder against the
          shutters; inside, every scratch of the nib was a small act of
          preservation against the dark and the coming centuries.
        </p>
        <p class="preview-well__mono calliope-mono">
          ¶ §&nbsp;I &nbsp;·&nbsp; In nomine
        </p>
      </div>
    </section>

  </div>
</template>

<style scoped>
/* Route the panel's main vertical gap through the density scale. */
.appearance-panel {
  display: flex;
  flex-direction: column;
  gap: var(--calliope-space-lg);
}

.font-section {
  gap: var(--calliope-space-md);
}

/* ─── Palette gallery ───────────────────────────────────────────────────────── */

.palette-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--calliope-space-sm);
}

.palette-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--calliope-space-xs);
  padding: var(--calliope-space-sm) var(--calliope-space-sm) var(--calliope-space-xs);
  background: transparent;
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-md);
  color: var(--calliope-paper);
  cursor: pointer;
  text-align: left;
  transition:
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    background-color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.palette-card:hover {
  background: var(--calliope-overlay-hover);
  border-color: var(--calliope-border-strong);
}

.palette-card:focus-visible {
  outline: 2px solid var(--calliope-bronze);
  outline-offset: 2px;
}

.palette-card.is-active {
  border-color: var(--calliope-bronze);
  background: var(--calliope-bronze-veil);
}

.palette-swatches {
  display: flex;
  gap: 3px;
  width: 100%;
}

.palette-swatch {
  height: 22px;
  flex: 1;
  border-radius: var(--calliope-radius-xs);
}

.palette-card__name {
  font-family: var(--calliope-font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--calliope-paper-muted);
  line-height: 1.2;
}

.palette-card.is-active .palette-card__name {
  color: var(--calliope-paper);
}

.palette-card__active-dot {
  position: absolute;
  top: 0.6rem;
  right: 0.65rem;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--calliope-bronze);
  box-shadow: 0 0 0 4px var(--calliope-bronze-veil);
}

/* ─── Accent row ────────────────────────────────────────────────────────────── */

.accent-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--calliope-space-xs);
}

.accent-swatch-btn {
  position: relative;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  background: var(--swatch-color, var(--calliope-paper-faint));
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--calliope-ink);
  transition:
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    transform var(--calliope-duration-fast) var(--calliope-ease-spring);
}

.accent-swatch-btn:hover {
  transform: scale(1.1);
}

.accent-swatch-btn:focus-visible {
  outline: 2px solid var(--calliope-bronze);
  outline-offset: 2px;
}

.accent-swatch-btn.is-active {
  border-color: var(--calliope-paper);
  box-shadow: 0 0 0 1px var(--calliope-bronze-glow);
}

.accent-swatch-btn--custom {
  background: var(--swatch-color, var(--calliope-ink-top));
  border-color: var(--calliope-border-strong);
  color: var(--calliope-paper-muted);
}

.accent-swatch-btn--custom.is-active {
  border-color: var(--calliope-bronze);
  color: var(--calliope-paper);
}

/* Visually hidden; triggered programmatically via colorPickerRef.click() */
.accent-color-input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.accent-reset-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px var(--calliope-space-xs);
  background: transparent;
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-pill);
  color: var(--calliope-paper-dim);
  font-family: var(--calliope-font-mono);
  font-size: 0.65rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  cursor: pointer;
  transition:
    border-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out);
}

.accent-reset-btn:hover {
  border-color: var(--calliope-bronze);
  color: var(--calliope-paper);
}

.accent-reset-btn:focus-visible {
  outline: 2px solid var(--calliope-bronze);
  outline-offset: 2px;
}

/* ─── Segmented control (shared by text-size + density) ──────────────────────── */

.segmented-control {
  display: inline-flex;
  background: var(--calliope-ink-soft);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-md);
  padding: 3px;
  gap: 2px;
}

.segmented-control__option {
  flex: 1;
  padding: 0.42rem var(--calliope-space-md);
  background: transparent;
  border: none;
  border-radius: var(--calliope-radius-sm);
  color: var(--calliope-paper-muted);
  font-family: var(--calliope-font-body);
  font-size: 0.82rem;
  letter-spacing: -0.005em;
  cursor: pointer;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    color var(--calliope-duration-fast) var(--calliope-ease-out);
  white-space: nowrap;
}

.segmented-control__option:hover {
  color: var(--calliope-paper);
}

.segmented-control__option:focus-visible {
  outline: 2px solid var(--calliope-bronze);
  outline-offset: -2px;
  border-radius: var(--calliope-radius-sm);
}

.segmented-control__option.is-active {
  background: var(--calliope-ink-top);
  color: var(--calliope-paper);
  box-shadow: 0 0 0 1px var(--calliope-bronze-veil);
}

/* ─── Font grid ─────────────────────────────────────────────────────────────── */

.font-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--calliope-space-sm);
}

.font-option__button {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--calliope-space-2xs);
  padding: var(--calliope-space-sm) var(--calliope-space-sm) var(--calliope-space-xs);
  background: transparent;
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-md);
  color: var(--calliope-paper);
  cursor: pointer;
  text-align: left;
  transition:
    background-color var(--calliope-duration-fast) var(--calliope-ease-out),
    border-color var(--calliope-duration-fast) var(--calliope-ease-out);
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

/* Fade unloaded font previews so the unstyled flash is less jarring. */
.font-option__button.is-loading .font-option__sample {
  opacity: 0.38;
}

.font-option__sample {
  font-size: 1.65rem;
  line-height: 1.05;
  letter-spacing: -0.012em;
  color: var(--calliope-paper);
  transition: opacity var(--calliope-duration-base) var(--calliope-ease-out);
}

.font-option__label {
  font-family: var(--calliope-font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--calliope-paper-muted);
}

.font-option__button.is-active .font-option__label {
  color: var(--calliope-paper-muted);
}

/* ─── Live preview well ─────────────────────────────────────────────────────── */

.preview-well {
  background: var(--calliope-ink-soft);
  border: 1px solid var(--calliope-border);
  border-radius: var(--calliope-radius-md);
  padding: var(--calliope-space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--calliope-space-sm);
}

.preview-well__display {
  margin: 0;
  font-size: 1.6rem;
  color: var(--calliope-paper);
  font-family: var(--calliope-font-display);
}

.preview-well__body {
  margin: 0;
  font-family: var(--calliope-font-chat);
  font-size: 0.9375rem;
  line-height: 1.65;
  color: var(--calliope-paper-muted);
}

.preview-well__mono {
  margin: 0;
  font-size: 0.72rem;
  color: var(--calliope-bronze);
  letter-spacing: 0.1em;
}
</style>
