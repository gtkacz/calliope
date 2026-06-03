export type EditMode = "append" | "rewrite";

export interface FileContent {
  path: string;
  content: string;
}

export interface EditProposal {
  path: string;
  mode: EditMode;
  original_content: string;
  proposed_content: string;
  truncated: boolean;
}
