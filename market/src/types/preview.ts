export interface HighlightedSource {
  content: string;
  lines: number;
}

export type UnavailableReason = 'tooLarge' | 'unsupported';

export type FilePreview =
  | { kind: 'markdown'; content: string; sourceUrl: string }
  | { kind: 'text'; source: HighlightedSource }
  | { kind: 'image'; url: string }
  | { kind: 'unavailable'; reason: UnavailableReason };

export interface PreviewFile {
  path: string;
  source: string;
}

export interface FilePreviewData {
  file: PreviewFile;
  preview: FilePreview;
}
