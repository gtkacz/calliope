import { requestJson } from '@/shared/api/client'

import type { Profile, ProfileCapability, ProfileKind } from './types'

export interface ProfilePayload {
  name: string
  kind: ProfileKind
  base_url: string
  model: string
  api_key_ref: string | null
  capabilities: ProfileCapability[]
  max_tokens: number | null
}

export interface ProfileTestResult {
  ok: boolean
  id: string
  capabilities: ProfileCapability[]
}

export function listProfiles(): Promise<Profile[]> {
  return requestJson('/v1/profiles')
}

export function createProfile(payload: ProfilePayload): Promise<Profile> {
  return requestJson('/v1/profiles', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function patchProfile(
  profileId: string,
  payload: Partial<ProfilePayload>,
): Promise<Profile> {
  return requestJson(`/v1/profiles/${profileId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteProfile(profileId: string): Promise<void> {
  return requestJson(`/v1/profiles/${profileId}`, { method: 'DELETE' })
}

export function testProfile(profileId: string): Promise<ProfileTestResult> {
  return requestJson(`/v1/profiles/${profileId}/test`, { method: 'POST' })
}
