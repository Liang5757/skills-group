import { useEffect, useState } from 'react';
import type { CSSProperties, ReactElement } from 'react';
import { useMessages } from '../../i18n/context.ts';
import { isHighlightedSource } from '../../lib/previewData.ts';
import type { FilePreviewData, HighlightedSource } from '../../types/preview.ts';
import styles from './FileContent.module.css';

interface SourceCodeProps {
  path: string;
  source: HighlightedSource;
}

function SourceCode({ path, source }: SourceCodeProps) {
  const marker = `<span class="${styles.lineNumber}" aria-hidden="true"></span>`;
  let line = 0;
  // Inline markers preserve the original newlines and let wrapped rows keep one number.
  const numbered = source.content.replace(/^|\n/g, (separator) => separator + (++line <= source.lines ? marker : ''));
  const style: CSSProperties & { '--line-number-width': string } = {
    '--line-number-width': `${String(source.lines).length}ch`,
  };
  return (
    <pre className={styles.sourceCode} tabIndex={0} aria-label={path} style={style}>
      <code className={styles.sourceText} dangerouslySetInnerHTML={{ __html: numbered }} />
    </pre>
  );
}

function MarkdownSource({ path, url }: { path: string; url: string }) {
  const { detail } = useMessages();
  const [source, setSource] = useState<HighlightedSource | 'unavailable' | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) throw new Error(`Source returned ${response.status}`);
        const data: unknown = await response.json();
        if (!isHighlightedSource(data)) throw new Error('Unexpected highlighted source');
        if (!controller.signal.aborted) setSource(data);
      } catch {
        if (!controller.signal.aborted) setSource('unavailable');
      }
    }
    void load();
    return () => controller.abort();
  }, [url]);

  if (source && source !== 'unavailable') return <SourceCode path={path} source={source} />;
  return (
    <p className={styles.previewMessage} role="status">
      {source === 'unavailable' ? detail.sourceUnavailable : detail.loadingSource}
    </p>
  );
}

// Markdown and source HTML come from the build renderer with raw Markdown HTML disabled.
export function FileContent({ file, preview, showSource }: FilePreviewData & { showSource: boolean }): ReactElement {
  const { detail } = useMessages();
  switch (preview.kind) {
    case 'markdown':
      return showSource ? (
        <MarkdownSource path={file.path} url={preview.sourceUrl} />
      ) : (
        <div className={styles.markdown} dangerouslySetInnerHTML={{ __html: preview.content }} />
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
