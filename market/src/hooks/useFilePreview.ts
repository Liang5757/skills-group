import { useEffect, useRef, useState } from 'react';
import type { FilePreviewData } from '../types/preview.ts';
import type { SkillFileLink } from '../types/skill.ts';
import { isFilePreviewData } from '../lib/previewData.ts';

export function useFilePreview(initial: FilePreviewData, assetQuery: string) {
  const [active, setActive] = useState(initial);
  const [pending, setPending] = useState(false);
  const request = useRef<AbortController | null>(null);

  useEffect(() => () => request.current?.abort(), []);

  async function select(file: SkillFileLink, url: string) {
    request.current?.abort();
    request.current = null;
    if (file.path === active.file.path) {
      setPending(false);
      return false;
    }

    const controller = new AbortController();
    request.current = controller;
    setPending(true);
    try {
      const previewUrl = new URL(`preview.json${assetQuery}`, url);
      const response = await fetch(previewUrl, { signal: controller.signal });
      if (!response.ok) throw new Error(`Preview returned ${response.status}`);
      const data: unknown = await response.json();
      if (controller.signal.aborted) return false;
      if (!isFilePreviewData(data) || data.file.path !== file.path) throw new Error('Unexpected file preview');

      const page = new URL(url);
      page.hash = '';
      window.history.replaceState(window.history.state, '', page);
      setActive(data);
      return true;
    } catch {
      if (!controller.signal.aborted) window.location.replace(url);
      return false;
    } finally {
      if (request.current === controller) {
        request.current = null;
        setPending(false);
      }
    }
  }

  return { active, pending, select };
}
