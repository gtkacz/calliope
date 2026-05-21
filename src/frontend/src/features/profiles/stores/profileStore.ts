import { defineStore } from 'pinia'

import * as profileApi from '../api'
import type { ProfilePayload, ProfileTestResult } from '../api'
import type { Profile } from '../types'

interface ProfileState {
  profiles: Profile[]
  loading: boolean
  errorMessage: string | null
  testResult: ProfileTestResult | null
}

export const useProfileStore = defineStore('profiles', {
  state: (): ProfileState => ({
    profiles: [],
    loading: false,
    errorMessage: null,
    testResult: null,
  }),
  getters: {
    chatProfiles(state): Profile[] {
      return state.profiles.filter((profile) => profile.capabilities.includes('chat'))
    },
  },
  actions: {
    async refresh() {
      this.loading = true
      this.errorMessage = null
      try {
        this.profiles = await profileApi.listProfiles()
      } catch (error) {
        this.errorMessage = error instanceof Error ? error.message : 'Could not load profiles.'
      } finally {
        this.loading = false
      }
    },
    async saveProfile(payload: ProfilePayload, profileId: string | null = null) {
      const saved =
        profileId === null
          ? await profileApi.createProfile(payload)
          : await profileApi.patchProfile(profileId, payload)
      const index = this.profiles.findIndex((profile) => profile.id === saved.id)
      if (index === -1) this.profiles.push(saved)
      else this.profiles.splice(index, 1, saved)
    },
    async deleteProfile(profileId: string) {
      await profileApi.deleteProfile(profileId)
      this.profiles = this.profiles.filter((profile) => profile.id !== profileId)
    },
    async testProfile(profileId: string) {
      this.testResult = await profileApi.testProfile(profileId)
    },
  },
})
