import type { SkillFileLink } from '../types/skill.ts';

export interface FileTreeNode {
  files: SkillFileLink[];
  folders: Map<string, FileTreeNode>;
}

export function parentFolders(path: string) {
  const parts = path.split('/').slice(0, -1);
  return parts.map((_, index) => parts.slice(0, index + 1).join('/'));
}

export function buildFileTree(files: readonly SkillFileLink[]): FileTreeNode {
  const root: FileTreeNode = { files: [], folders: new Map() };
  for (const file of files) {
    let parent = root;
    for (const path of parentFolders(file.path)) {
      let folder = parent.folders.get(path);
      if (!folder) {
        folder = { files: [], folders: new Map() };
        parent.folders.set(path, folder);
      }
      parent = folder;
    }
    if (file.path === 'SKILL.md') parent.files.unshift(file);
    else parent.files.push(file);
  }
  return root;
}
