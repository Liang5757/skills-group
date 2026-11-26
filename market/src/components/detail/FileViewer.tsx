import * as ToggleGroup from '@radix-ui/react-toggle-group';
import { useMessages } from '../../i18n/context.ts';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { MouseEvent } from 'react';
import { usePageMetadata } from '../../hooks/usePageMetadata.ts';
import type { FilePreviewData } from '../../types/preview.ts';
import type { SkillDetails } from '../../types/skill.ts';
import { FileContent } from './FileContent.tsx';
import { FileTree } from './FileTree.tsx';
import { buildFileTree, parentFolders } from '../../lib/fileTree.ts';
import { useFilePreview } from '../../hooks/useFilePreview.ts';
import styles from './FileViewer.module.css';
import layout from '../../styles/layout.module.css';
import controls from '../../styles/controls.module.css';

interface FileViewerProps {
  skill: SkillDetails;
  initial: FilePreviewData;
  root: string;
  assetQuery: string;
  interactive: boolean;
}

export function FileViewer({ skill, initial, root, assetQuery, interactive }: FileViewerProps) {
  const messages = useMessages();
  const { detail } = messages;
  const { active, pending, select } = useFilePreview(initial, assetQuery);
  const { file, preview } = active;
  usePageMetadata(messages, { skill, file });
  const [sourcePath, setSourcePath] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(true);
  const [openFolders, setOpenFolders] = useState(() => new Set(parentFolders(initial.file.path)));
  const tree = useMemo(() => buildFileTree(skill.files), [skill.files]);
  const viewer = useRef<HTMLElement>(null);
  const previewArea = useRef<HTMLElement>(null);
  const treeNav = useRef<HTMLElement>(null);
  const panelSummary = useRef<HTMLElement>(null);
  const focusFile = useRef(false);
  const showSource = sourcePath === file.path;

  function revealPreview() {
    const panel = viewer.current;
    if (!panel) return;
    const { top } = panel.getBoundingClientRect();
    if (top < 0 || top > window.innerHeight - 100) panel.scrollIntoView({ block: 'start' });
  }

  useEffect(() => {
    if (active === initial) return;
    revealPreview();
    if (focusFile.current) {
      const disclosure = panelSummary.current?.parentElement;
      const target =
        disclosure instanceof HTMLDetailsElement && disclosure.open
          ? treeNav.current?.querySelector<HTMLElement>('[aria-current="page"]')
          : panelSummary.current;
      target?.focus({ preventScroll: true });
      focusFile.current = false;
    }
  }, [active, initial]);

  async function handleLink(event: MouseEvent<HTMLElement>) {
    const link = event.target instanceof Element && event.target.closest<HTMLAnchorElement>('a[href]');
    if (
      !link ||
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    )
      return;
    if (link.target || link.origin !== window.location.origin || link.hash !== '#preview') return;
    const base = new URL(root, window.location.href);
    const selected = skill.files.find((entry) => new URL(entry.href, base).pathname === link.pathname);
    if (!selected) return;

    event.preventDefault();
    const restoreFocus = event.detail === 0 && previewArea.current?.contains(link) === true;
    const sameFile = selected.path === file.path;
    if (await select(selected, link.href)) {
      focusFile.current = restoreFocus && document.activeElement === link;
      setSourcePath(null);
      setOpenFolders((folders) => new Set([...folders, ...parentFolders(selected.path)]));
    } else if (sameFile) {
      revealPreview();
    }
  }

  function toggleFolder(path: string) {
    setOpenFolders((previous) => {
      const folders = new Set(previous);
      if (folders.has(path)) folders.delete(path);
      else folders.add(path);
      return folders;
    });
  }

  return (
    <>
      <section
        className={styles.fileViewer}
        id="preview"
        ref={viewer}
        aria-labelledby="preview-title"
        onClick={handleLink}
      >
        <header className={styles.previewBar}>
          <div className={styles.previewFileHeading}>
            <h2 className={styles.previewTitle} id="preview-title">
              <code className={styles.previewPath}>{file.path}</code>
            </h2>
          </div>
          <div className={styles.previewActions}>
            {preview.kind === 'markdown' && (
              <ToggleGroup.Root
                className={controls.segmented}
                type="single"
                aria-label={detail.viewMode}
                hidden={!interactive}
                value={showSource ? 'source' : 'preview'}
                onValueChange={(mode) => {
                  if (mode) setSourcePath(mode === 'source' ? file.path : null);
                }}
              >
                <ToggleGroup.Item className={controls.segmentedItem} value="preview">
                  {detail.preview}
                </ToggleGroup.Item>
                <ToggleGroup.Item className={controls.segmentedItem} value="source">
                  {detail.code}
                </ToggleGroup.Item>
              </ToggleGroup.Root>
            )}
            <a className={controls.sourceLink} href={file.source}>
              {detail.viewOnGitHub}{' '}
              <span className={controls.sourceArrow} aria-hidden="true">
                ↗
              </span>
            </a>
          </div>
        </header>
        <div className={styles.viewerBody}>
          <FileTree
            className={styles.treePanel}
            tree={tree}
            activePath={file.path}
            root={root}
            panelOpen={panelOpen}
            openFolders={openFolders}
            onTogglePanel={() => setPanelOpen((open) => !open)}
            onToggleFolder={toggleFolder}
            treeRef={treeNav}
            summaryRef={panelSummary}
          />
          <article
            className={styles.preview}
            aria-labelledby="preview-title"
            aria-busy={pending || undefined}
            ref={previewArea}
          >
            <FileContent key={file.path} file={file} preview={preview} showSource={showSource} />
          </article>
        </div>
      </section>
      <span className={layout.visuallyHidden} role="status">
        {active !== initial && detail.opened(file.path)}
      </span>
    </>
  );
}
