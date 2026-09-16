import type { InjectionKey } from 'vue'

export interface DraftGuard {
  isDirty: () => boolean
  discard: () => void
}

export interface DraftGuardController {
  register: (guard: DraftGuard) => () => void
  requestDiscard: (action: () => void) => void
}

export const draftGuardKey: InjectionKey<DraftGuardController> = Symbol('settings-draft-guard')
