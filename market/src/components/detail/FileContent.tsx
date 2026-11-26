import type { CSSProperties, ReactElement } from 'react';
import { useMessages } from '../../i18n/context.ts';
import type { FilePreviewData, HighlightedSource } from '../../types/preview.ts';
import styles from './FileContent.module.css';

interface SourceCodeProps {
  path: string;
  source: HighlightedSource;
  hidden?: boolean;
}

function SourceCode({ path, source, hidden }: SourceCodeProps) {
  const marker = `<span class="${styles.lineNumber}" aria-hidden="true"></span>`;
  let line = 0;
  // Inline markers preserve the original newlines and let wrapped rows keep one number.
  const numbered = source.content.replace(/^|\n/g, (separator) => separator + (++line <= source.lines ? marker : ''));
  const style: CSSProperties & { '--line-number-width': string } = {
    '--line-number-width': `${String(source.lines).length}ch`,
  };
  return (
    <pre className={styles.sourceCode} tabIndex={0} aria-label={path} hidden={hidden} style={style}>
      <code className={styles.sourceText} dangerouslySetInnerHTML={{ __html: numbered }} />
    </pre>
  );
}

// Markdown and source HTML come from the build renderer with raw Markdown HTML disabled.
export function FileContent({ file, preview, showSource }: FilePreviewData & { showSource: boolean }): ReactElement {
  const { detail } = useMessages();
  switch (preview.kind) {
    case 'markdown':
      return (
        <>
          <div className={styles.markdown} hidden={showSource} dangerouslySetInnerHTML={{ __html: preview.content }} />
          <SourceCode path={file.path} source={preview.source} hidden={!showSource} />
        </>
      );
    case 'text':
      return <SourceCode path={file.path} source={preview.source} />;
    case 'image':
      return (
        <div className={styles.imagePreview}>
          <img className={styles.previewImage} src={preview.url} alt={file.path} loading="lazy" />
        </div>
      );
    case 'unavailable':
      return (
        <p className={styles.previewMessage}>{detail.unavailable[preview.reason] ?? detail.unavailable.unsupported}</p>
      );
  }
}
