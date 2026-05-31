/**
 * Lazily injects a single combined Google Fonts <link> for decorative font families
 * that have not yet been requested. Using a module-level Set means the injection is
 * idempotent across multiple call sites and Vue component re-mounts.
 */

const GOOGLE_FONTS_MAP: Record<string, string> = {
  amarante: 'Amarante',
  metamorphous: 'Metamorphous',
  'macondo-swash-caps': 'Macondo+Swash+Caps',
  'cormorant-unicase': 'Cormorant+Unicase:wght@400;500;600;700',
  'pirata-one': 'Pirata+One',
  'grenze-gotisch': 'Grenze+Gotisch:wght@400;500;600;700',
  'germania-one': 'Germania+One',
  astloch: 'Astloch:wght@400;700',
  'almendra-sc': 'Almendra+SC',
  texturina: 'Texturina:opsz,wght@12..72,400;12..72,500;12..72,600',
  'nova-cut': 'Nova+Cut',
  'jim-nightshade': 'Jim+Nightshade',
  almendra: 'Almendra:ital,wght@0,400;0,700;1,400;1,700',
  quintessential: 'Quintessential',
  fondamento: 'Fondamento:ital@0;1',
  cormorant: 'Cormorant:ital,wght@0,300..700;1,300..700',
}

const injectedFamilies = new Set<string>()

/**
 * Ensures the given font IDs (from DISPLAY_FONTS / CHAT_FONTS) are loaded via
 * Google Fonts. Unknown IDs (e.g. 'fraunces', 'geist' which are self-hosted via
 * fontsource) are silently skipped.
 *
 * Returns a Promise that resolves once document.fonts.ready fires, giving the
 * browser a chance to parse and apply the newly injected stylesheet.
 *
 * This is a pure utility function — it has no Vue lifecycle coupling so it can
 * safely be called from store actions, outside of setup(), etc.
 */
export function ensureFontsLoaded(fontIds: string[]): Promise<void> {
  if (typeof document === 'undefined') {
    return Promise.resolve()
  }

  const newFamilies = fontIds
    .filter((id) => id in GOOGLE_FONTS_MAP && !injectedFamilies.has(id))
    .map((id) => {
      injectedFamilies.add(id)
      return GOOGLE_FONTS_MAP[id]
    })

  if (newFamilies.length > 0) {
    const familyParams = newFamilies.map((f) => `family=${f}`).join('&')
    const href = `https://fonts.googleapis.com/css2?${familyParams}&display=swap`

    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = href
    document.head.appendChild(link)
  }

  return document.fonts.ready.then(() => undefined)
}

const injectedStylesheets = new Set<string>()

/**
 * Injects a single stylesheet <link> for an arbitrary (already validated) font
 * import URL — used by user-added custom fonts, whose URLs are not known to the
 * built-in GOOGLE_FONTS_MAP. The module-level Set keeps this idempotent across
 * store re-initialisation and repeated add calls.
 */
export function injectFontStylesheet(href: string): void {
  if (typeof document === 'undefined') return
  if (injectedStylesheets.has(href)) return
  injectedStylesheets.add(href)

  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = href
  document.head.appendChild(link)
}
