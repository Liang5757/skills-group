import { useEffect, useMemo, useState } from 'react';
import { createCatalogIndex, readCatalogPage } from '../lib/catalog.ts';
import type { SkillListing } from '../types/skill.ts';

interface CatalogLocation {
  query: string;
  page: number;
}

function saveCatalogLocation(query: string, page: number) {
  const url = new URL(window.location.href);
  if (query.trim()) url.searchParams.set('q', query.trim());
  else url.searchParams.delete('q');
  if (page > 1) url.searchParams.set('page', String(page));
  else url.searchParams.delete('page');
  if (url.href !== window.location.href) window.history.replaceState(window.history.state, '', url);
}

export function useCatalog(skills: readonly SkillListing[]) {
  const [location, setLocation] = useState<CatalogLocation | null>(null);
  const entries = useMemo(() => createCatalogIndex(skills), [skills]);
  const query = location?.query ?? '';
  const page = readCatalogPage(entries, query, location?.page ?? 1);

  useEffect(() => {
    function restore() {
      const params = new URLSearchParams(window.location.search);
      const restoredQuery = params.get('q') ?? '';
      const { current } = readCatalogPage(entries, restoredQuery, Number(params.get('page')));
      setLocation({ query: restoredQuery, page: current });
      saveCatalogLocation(restoredQuery, current);
    }
    restore();
    window.addEventListener('pageshow', restore);
    return () => window.removeEventListener('pageshow', restore);
  }, [entries]);

  function changeQuery(next: string) {
    setLocation({ query: next, page: 1 });
    saveCatalogLocation(next, 1);
  }

  function changePage(next: number) {
    setLocation({ query, page: next });
    saveCatalogLocation(query, next);
  }

  return { ready: location !== null, entries, query, ...page, changeQuery, changePage };
}
