import { isRecord } from './isRecord.ts';
import type { FilePreview, FilePreviewData, HighlightedSource } from '../types/preview.ts';

function isHighlightedSource(value: unknown): value is HighlightedSource {
  return (
    isRecord(value) &&
    typeof value.content === 'string' &&
    typeof value.lines === 'number' &&
    Number.isSafeInteger(value.lines) &&
    value.lines >= 1
  );
}

function isFilePreview(value: unknown): value is FilePreview {
  if (!isRecord(value)) return false;
  switch (value.kind) {
    case 'markdown':
      return typeof value.content === 'string' && isHighlightedSource(value.source);
    case 'text':
      return isHighlightedSource(value.source);
    case 'image':
      return typeof value.url === 'string';
    case 'unavailable':
      return value.reason === 'tooLarge' || value.reason === 'unsupported';
    default:
      return false;
  }
}

export function isFilePreviewData(value: unknown): value is FilePreviewData {
  return (
    isRecord(value) &&
    isRecord(value.file) &&
    typeof value.file.path === 'string' &&
    typeof value.file.source === 'string' &&
    isFilePreview(value.preview)
  );
}
