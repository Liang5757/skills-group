import { useMessages } from '../../i18n/context.ts';
import { useEffect, useRef, useState } from 'react';
import styles from './InstallPanel.module.css';
import layout from '../../styles/layout.module.css';
import controls from '../../styles/controls.module.css';

export function InstallPanel({ command, interactive }: { command: string; interactive: boolean }) {
  const { install } = useMessages();
  const [feedback, setFeedback] = useState<'copied' | 'manual' | null>(null);
  const commandText = useRef<HTMLElement>(null);
  const timer = useRef<number | undefined>(undefined);
  const message = feedback ? install[feedback] : null;

  useEffect(() => () => window.clearTimeout(timer.current), []);

  async function copy() {
    window.clearTimeout(timer.current);
    try {
      await navigator.clipboard.writeText(command);
      setFeedback('copied');
    } catch {
      const selection = window.getSelection();
      if (!selection || !commandText.current) return;
      const range = document.createRange();
      range.selectNodeContents(commandText.current);
      selection.removeAllRanges();
      selection.addRange(range);
      setFeedback('manual');
    }
    timer.current = window.setTimeout(() => setFeedback(null), 2500);
  }

  return (
    <section className={styles.installPanel}>
      <div className={styles.installHeading}>
        <h2 className={styles.installTitle}>{install.title}</h2>
        <span className={styles.installRequirement} aria-label={install.requirement}>
          Node.js 22.20+
        </span>
      </div>
      <div className={styles.commandPanel}>
        <pre className={styles.command}>
          <code className={styles.commandText} ref={commandText}>
            {command}
          </code>
        </pre>
        <button
          className={`${controls.button} ${controls.buttonPrimary}`}
          type="button"
          hidden={!interactive}
          onClick={copy}
        >
          {message?.label ?? install.copy}
        </button>
      </div>
      <span className={layout.visuallyHidden} role="status">
        {message?.message}
      </span>
    </section>
  );
}
