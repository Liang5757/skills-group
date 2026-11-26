import type { FormEvent } from 'react';
import { useMessages } from '../../i18n/context.ts';
import styles from './CatalogPagination.module.css';
import controls from '../../styles/controls.module.css';

interface CatalogPaginationProps {
  page: number;
  pageCount: number;
  onChange: (page: number) => void;
}

export function CatalogPagination({ page, pageCount, onChange }: CatalogPaginationProps) {
  const { pagination } = useMessages();
  function jump(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem('page');
    if (input instanceof HTMLInputElement) onChange(input.valueAsNumber);
  }

  return (
    <nav className={styles.pagination} aria-label={pagination.navigation}>
      <div className={styles.pageControls}>
        <button className={controls.button} type="button" disabled={page === 1} onClick={() => onChange(page - 1)}>
          {pagination.previous}
        </button>
        <span className={styles.pageStatus} role="status">
          {pagination.page(page, pageCount)}
        </span>
        <button
          className={controls.button}
          type="button"
          disabled={page === pageCount}
          onClick={() => onChange(page + 1)}
        >
          {pagination.next}
        </button>
      </div>
      <form className={styles.pageJump} onSubmit={jump}>
        <label className={styles.pageLabel} htmlFor="skill-page">
          {pagination.jumpTo}
        </label>
        <input
          className={`${controls.input} ${styles.pageInput}`}
          key={`${page}/${pageCount}`}
          type="number"
          id="skill-page"
          name="page"
          min="1"
          max={pageCount}
          step="1"
          required
          aria-label={pagination.pageNumber}
          defaultValue={page}
        />
        <button className={controls.button} type="submit">
          {pagination.jump}
        </button>
      </form>
    </nav>
  );
}
