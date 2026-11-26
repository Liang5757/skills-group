import { useMessages } from '../../i18n/context.ts';
import type { SkillPageData } from '../../types/page.ts';
import { VersionBadge } from '../shared/VersionBadge.tsx';
import { FileViewer } from './FileViewer.tsx';
import { InstallPanel } from './InstallPanel.tsx';
import styles from './SkillPage.module.css';
import layout from '../../styles/layout.module.css';
import controls from '../../styles/controls.module.css';

type SkillPageProps = Omit<SkillPageData, 'kind'> & { interactive: boolean };

export function SkillPage({ skill, initial, root, site, interactive }: SkillPageProps) {
  const { catalog, detail } = useMessages();
  return (
    <main className={layout.page} id="main">
      <header className={styles.detailHeading}>
        <div>
          <nav aria-label={detail.navigation}>
            <a className={styles.backLink} href={root}>
              <span aria-hidden="true">←</span> {catalog.all}
            </a>
          </nav>
          <div className={styles.titleRow}>
            <h1 className={styles.skillTitle}>{skill.name}</h1>
            <VersionBadge version={skill.version} className={styles.skillVersion} />
          </div>
          <p className={styles.skillDescription}>{skill.description}</p>
        </div>
        <InstallPanel command={skill.command} interactive={interactive} />
      </header>
      <FileViewer skill={skill} initial={initial} root={root} assetQuery={site.assetQuery} interactive={interactive} />
      <p className={styles.skillSource}>
        {detail.source}{' '}
        <a className={`${controls.sourceLink} ${styles.skillSourceLink}`} href={skill.source}>
          {site.repository}{' '}
          <span className={controls.sourceArrow} aria-hidden="true">
            ↗
          </span>
        </a>
      </p>
    </main>
  );
}
