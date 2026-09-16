import { defineStore } from 'pinia'

import * as workspaceApi from '../api'
import type { WorkspacePayload } from '../api'
import type { ReindexResponse, Workspace } from '../types'

interface WorkspaceState {
  workspaces: Workspace[]
  selectedWorkspaceId: string | null
  loading: boolean
  reindexing: boolean
  errorMessage: string | null
  reindexResult: ReindexResponse | null
}

export const useWorkspaceStore = defineStore('workspaces', {
  state: (): WorkspaceState => ({
    workspaces: [],
    selectedWorkspaceId: null,
    loading: false,
    reindexing: false,
    errorMessage: null,
    reindexResult: null,
  }),
  getters: {
    selectedWorkspace(state): Workspace | null {
      return (
        state.workspaces.find((workspace) => workspace.id === state.selectedWorkspaceId) ?? null
      )
    },
  },
  actions: {
    async refresh() {
      this.loading = true
      this.errorMessage = null
      try {
        this.workspaces = await workspaceApi.listWorkspaces()
        if (this.selectedWorkspaceId === null && this.workspaces.length > 0) {
          this.selectedWorkspaceId = this.workspaces[0].id
        }
      } catch (error) {
        this.errorMessage = error instanceof Error ? error.message : 'Could not load workspaces.'
      } finally {
        this.loading = false
      }
    },
    async saveWorkspace(payload: WorkspacePayload, workspaceId: string | null = null) {
      this.errorMessage = null
      try {
        const saved =
          workspaceId === null
            ? await workspaceApi.createWorkspace(payload)
            : await workspaceApi.patchWorkspace(workspaceId, payload)
        const index = this.workspaces.findIndex((workspace) => workspace.id === saved.id)
        if (index === -1) this.workspaces.push(saved)
        else this.workspaces.splice(index, 1, saved)
        this.selectedWorkspaceId = saved.id
        return saved
      } catch (error) {
        this.errorMessage = error instanceof Error ? error.message : 'Could not save workspace.'
        throw error
      }
    },
    async deleteWorkspace(workspaceId: string) {
      await workspaceApi.deleteWorkspace(workspaceId)
      this.workspaces = this.workspaces.filter((workspace) => workspace.id !== workspaceId)
      if (this.selectedWorkspaceId === workspaceId) {
        this.selectedWorkspaceId = this.workspaces[0]?.id ?? null
      }
    },
    async reindexSelectedWorkspace() {
      if (this.selectedWorkspaceId === null) return
      this.reindexing = true
      this.reindexResult = null
      this.errorMessage = null
      try {
        this.reindexResult = await workspaceApi.reindexWorkspace(this.selectedWorkspaceId)
      } catch (error) {
        this.errorMessage = error instanceof Error ? error.message : 'Reindex failed.'
      } finally {
        this.reindexing = false
      }
    },
  },
})
