import { useMessages } from '../../i18n/context.ts';
import styles from './VersionBadge.module.css';

export function VersionBadge({ version, className }: { version: string; className?: string }) {
  const { detail } = useMessages();
  return (
    <span className={className ? `${styles.version} ${className}` : styles.version}>
      {version ? `v${version.replace(/^v/i, '')}` : detail.versionMissing}
    </span>
  );
}
