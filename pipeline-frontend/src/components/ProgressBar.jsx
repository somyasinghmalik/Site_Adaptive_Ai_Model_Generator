import React from 'react';
import styles from './ProgressBar.module.css';

export default function ProgressBar({ percentage }) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.textContainer}>
        <span className={styles.statusLabel}>
          {percentage < 100 ? 'Analyzing remote site data assets...' : 'Extraction sequence completed'}
        </span>
        <span className={styles.percentageNum}>{percentage}%</span>
      </div>
      <div className={styles.track}>
        <div className={styles.fill} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}