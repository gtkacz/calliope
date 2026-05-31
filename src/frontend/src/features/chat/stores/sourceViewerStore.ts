import { defineStore } from "pinia";

import { getDocumentContent } from "@/features/documents/api";
import type { DocumentContent } from "@/features/documents/types";
import type { SourceReference } from "../types";

interface SourceViewerState {
  open: boolean;
  // The citation that opened the viewer — its heading/path label the dialog
  // while the full document content loads.
  source: SourceReference | null;
  content: DocumentContent | null;
  loading: boolean;
  errorMessage: string | null;
}

export const useSourceViewerStore = defineStore("sourceViewer", {
  state: (): SourceViewerState => ({
    open: false,
    source: null,
    content: null,
    loading: false,
    errorMessage: null,
  }),
  actions: {
    async show(source: SourceReference) {
      this.open = true;
      this.source = source;
      this.content = null;
      this.errorMessage = null;
      this.loading = true;
      // Capture the document id this request is for so a slow response from a
      // previously-opened source cannot overwrite a newer selection.
      const requestedDocumentId = source.document_id;
      try {
        const content = await getDocumentContent(
          source.document_id,
          source.chunk_id,
        );
        if (this.source?.document_id !== requestedDocumentId) return;
        this.content = content;
      } catch (error) {
        if (this.source?.document_id !== requestedDocumentId) return;
        this.errorMessage =
          error instanceof Error
            ? error.message
            : "Could not load the source document.";
      } finally {
        if (this.source?.document_id === requestedDocumentId) {
          this.loading = false;
        }
      }
    },
    hide() {
      this.open = false;
      this.source = null;
      this.content = null;
      this.errorMessage = null;
      this.loading = false;
    },
  },
});
