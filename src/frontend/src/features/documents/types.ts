export interface DocumentSummary {
  id: string;
  path: string;
  title: string;
}

export interface DocumentContent {
  id: string;
  path: string;
  title: string;
  content: string;
  passage: string | null;
}
