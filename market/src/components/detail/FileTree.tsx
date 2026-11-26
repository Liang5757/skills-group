import type { Ref } from 'react';
import { useMessages } from '../../i18n/context.ts';
import type { FileTreeNode } from '../../lib/fileTree.ts';
import styles from './FileTree.module.css';
import layout from '../../styles/layout.module.css';

interface TreeProps {
  activePath: string;
  openFolders: ReadonlySet<string>;
  onToggleFolder: (path: string) => void;
  root: string;
}

interface FileTreeProps extends TreeProps {
  className?: string;
  tree: FileTreeNode;
  panelOpen: boolean;
  onTogglePanel: () => void;
  summaryRef: Ref<HTMLElement>;
  treeRef: Ref<HTMLElement>;
}

function TreeItems({ node, activePath, openFolders, onToggleFolder, root }: TreeProps & { node: FileTreeNode }) {
  return (
    <ul className={styles.treeList}>
      {node.files.map((file) => {
        const name = file.path.split('/').at(-1);
        return (
          <li key={file.path}>
            <a
              className={styles.fileLink}
              href={`${root}${file.href}#preview`}
              title={name}
              aria-current={file.path === activePath ? 'page' : undefined}
            >
              {name}
            </a>
          </li>
        );
      })}
      {Array.from(node.folders, ([path, folder]) => (
        <li key={path}>
          <details className={styles.folder} open={openFolders.has(path)}>
            <summary
              className={styles.folderToggle}
              onClick={(event) => {
                event.preventDefault();
                onToggleFolder(path);
              }}
            >
              {path.split('/').at(-1)}
            </summary>
            <TreeItems
              node={folder}
              activePath={activePath}
              openFolders={openFolders}
              onToggleFolder={onToggleFolder}
              root={root}
            />
          </details>
        </li>
      ))}
    </ul>
  );
}

export function FileTree({
  className,
  tree,
  activePath,
  root,
  panelOpen,
  onTogglePanel,
  openFolders,
  onToggleFolder,
  summaryRef,
  treeRef,
}: FileTreeProps) {
  const { detail } = useMessages();
  return (
    <details className={className ? `${styles.filePanel} ${className}` : styles.filePanel} open={panelOpen}>
      <summary
        className={styles.filePanelHeader}
        ref={summaryRef}
        title={detail.toggleFiles}
        onClick={(event) => {
          event.preventDefault();
          onTogglePanel();
        }}
      >
        <span className={styles.filePanelIcon} aria-hidden="true" />
        <span className={`${styles.expandLabel} ${layout.visuallyHidden}`}>{detail.expandFiles}</span>
        <span className={`${styles.collapseLabel} ${layout.visuallyHidden}`}>{detail.collapseFiles}</span>
        <span className={styles.filePanelLabel} aria-hidden="true">
          {detail.directory}
        </span>
      </summary>
      <nav className={styles.fileTree} ref={treeRef} aria-label={detail.files}>
        <TreeItems
          node={tree}
          activePath={activePath}
          openFolders={openFolders}
          onToggleFolder={onToggleFolder}
          root={root}
        />
      </nav>
    </details>
  );
}
