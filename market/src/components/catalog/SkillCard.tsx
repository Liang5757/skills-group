import type { SkillListing } from '../../types/skill.ts';
import { VersionBadge } from '../shared/VersionBadge.tsx';
import styles from './SkillCard.module.css';

interface SkillCardProps {
  skill: SkillListing;
  root: string;
  hidden: boolean;
  viewSkill: string;
}

export function SkillCard({ skill, root, hidden, viewSkill }: SkillCardProps) {
  const titleId = `skill-${skill.name}`;
  return (
    <li className={styles.skillCard} hidden={hidden}>
      <a className={styles.cardLink} href={`${root}skills/${skill.name}/`} aria-labelledby={titleId}>
        <div className={styles.cardTop}>
          <h3 className={styles.cardTitle} id={titleId}>
            {skill.name}
          </h3>
          <VersionBadge version={skill.version} className={styles.cardVersion} />
        </div>
        <p className={styles.cardDescription}>{skill.description}</p>
        <span className={styles.cardAction} aria-hidden="true">
          {viewSkill} <span className={styles.cardArrow}>→</span>
        </span>
      </a>
    </li>
  );
}
