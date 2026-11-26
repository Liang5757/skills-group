import { ArrowTopRightIcon, GitHubLogoIcon } from '@radix-ui/react-icons';
import { useEffect, useState } from 'react';
import { useMessages } from '../i18n/context.ts';
import type { MarketPage } from '../types/page.ts';
import { CatalogPage } from '../components/catalog/CatalogPage.tsx';
import { SkillPage } from '../components/detail/SkillPage.tsx';
import { PreferenceControls } from '../components/preferences/PreferenceControls.tsx';
import { PreferencesProvider } from '../preferences/PreferencesProvider.tsx';
import '../theme/theme.css';
import '../styles/base.css';
import styles from './App.module.css';
import layout from '../styles/layout.module.css';
import controls from '../styles/controls.module.css';

export function App(props: MarketPage) {
  return (
    <PreferencesProvider>
      <MarketLayout {...props} />
    </PreferencesProvider>
  );
}

function MarketLayout(page: MarketPage) {
  const { site, root } = page;
  const { header } = useMessages();
  const [absoluteRoot, setAbsoluteRoot] = useState<string | null>(null);
  const base = absoluteRoot ?? root;
  const isCatalog = page.kind === 'catalog';
  useEffect(() => {
    setAbsoluteRoot(new URL(root, window.location.href).href);
  }, [root]);

  return (
    <>
      <a className={styles.skipLink} href="#main">
        {header.skip}
      </a>
      <header className={styles.siteHeader}>
        <div className={`${layout.frame} ${styles.headerInner}`}>
          <a className={styles.wordmark} href={base} aria-label={header.home}>
            <span className={styles.brandMark} aria-hidden="true" />
            Skills Group
          </a>
          <nav className={styles.headerNav} aria-label={header.navigation}>
            <a className={styles.marketLink} href={base} aria-current={isCatalog ? 'page' : undefined}>
              {header.market}
            </a>
            <a
              className={`${controls.button} ${controls.buttonGhost} ${styles.repositoryLink}`}
              href={site.github}
              aria-label="GitHub"
            >
              <GitHubLogoIcon className={controls.buttonGlyph} aria-hidden="true" />
              <span className={styles.repositoryLabel}>GitHub</span>
              <ArrowTopRightIcon className={`${controls.buttonGlyph} ${styles.repositoryArrow}`} aria-hidden="true" />
            </a>
          </nav>
          <PreferenceControls />
        </div>
      </header>
      {page.kind === 'catalog' ? (
        <CatalogPage skills={page.skills} root={base} />
      ) : (
        <SkillPage
          skill={page.skill}
          initial={page.initial}
          root={base}
          site={site}
          interactive={absoluteRoot !== null}
        />
      )}
    </>
  );
}
