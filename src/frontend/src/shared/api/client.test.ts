import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, requestJson } from './client'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('requestJson', () => {
  it('returns parsed JSON for successful responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }))))

    await expect(requestJson('/v1/example')).resolves.toEqual({ ok: true })
  })

  it('normalizes backend error envelopes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: 'workspace_not_found',
              message: 'Workspace not found.',
              details: { workspace_id: 'workspace_missing' },
            },
          }),
          { status: 404 },
        ),
      ),
    )

    await expect(requestJson('/v1/workspaces/workspace_missing')).rejects.toMatchObject({
      code: 'workspace_not_found',
      message: 'Workspace not found.',
      status: 404,
      details: { workspace_id: 'workspace_missing' },
    } satisfies Partial<ApiError>)
  })
})
