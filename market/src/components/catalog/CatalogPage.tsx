import { useRef } from 'react';
import { useCatalog } from '../../hooks/useCatalog.ts';
import { usePageMetadata } from '../../hooks/usePageMetadata.ts';
import { useMessages } from '../../i18n/context.ts';
import layout from '../../styles/layout.module.css';
import type { CatalogPageData } from '../../types/page.ts';
import { CatalogPagination } from './CatalogPagination.tsx';
import { SkillCard } from './SkillCard.tsx';
import styles from './CatalogPage.module.css';

export function CatalogPage({ skills, root }: Pick<CatalogPageData, 'skills' | 'root'>) {
  const messages = useMessages();
  const { catalog, header } = messages;
  usePageMetadata(messages);
  const { ready, entries, query, matches, current, pageCount, visible, changeQuery, changePage } = useCatalog(skills);
  const search = useRef<HTMLInputElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);

  function goToPage(page: number) {
    if (page === current) return;
    changePage(page);
    heading.current?.focus({ preventScroll: true });
    heading.current?.scrollIntoView({ block: 'start' });
  }

  return (
    <main className={layout.page} id="main">
      <header className={styles.catalogHeading}>
        <div>
          <h1 className={styles.pageTitle}>{header.market}</h1>
          <p className={styles.pageDescription}>{catalog.description}</p>
        </div>
        <label className={styles.search} hidden={!ready || skills.length === 0}>
          <span className={styles.searchIcon} aria-hidden="true" />
          <input
            className={styles.searchInput}
            type="search"
            id="skill-search"
            aria-label={catalog.search}
            placeholder={catalog.search}
            autoComplete="off"
            ref={search}
            value={query}
            onChange={(event) => changeQuery(event.target.value)}
          />
        </label>
      </header>
      <section aria-labelledby="catalog-title">
        <div className={styles.catalogTitle}>
          <h2 className={styles.skillsTitle} id="catalog-title" tabIndex={-1} ref={heading}>
            {catalog.all}
          </h2>
          <span className={styles.skillCount} id="skill-count" role="status">
            {catalog.count(matches.length)}
          </span>
        </div>
        <ul className={styles.skillGrid}>
          {entries.map((entry) => (
            <SkillCard
              key={entry.skill.name}
              skill={entry.skill}
              root={root}
              hidden={ready && !visible.has(entry)}
              viewSkill={catalog.viewSkill}
            />
          ))}
        </ul>
        {matches.length === 0 && (
          <div className={styles.emptyState}>
            <p className={styles.emptyMessage}>{skills.length ? catalog.noResults : catalog.empty}</p>
            {skills.length > 0 && (
              <button
                className={styles.textButton}
                type="button"
                onClick={() => {
                  search.current?.focus();
                  changeQuery('');
                }}
              >
                {catalog.clearSearch}
              </button>
            )}
          </div>
        )}
        {ready && pageCount > 1 && <CatalogPagination page={current} pageCount={pageCount} onChange={goToPage} />}
      </section>
    </main>
  );
}
