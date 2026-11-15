import type { MatchQuality } from '../types/contract';
import { MATCH_QUALITY_STYLES } from '../lib/matchQuality';

export interface ScoreRingProps {
  /** 0–100 match score. */
  score: number;
  /** Colours the ring; comes from the analog's match_quality. */
  quality: MatchQuality;
  /** Diameter in px. */
  size?: number;
}

/** The match score inside a ring that fills in proportion to the score (100 = full circle). */
export function ScoreRing({ score, quality, size = 44 }: ScoreRingProps) {
  const style = MATCH_QUALITY_STYLES[quality];
  const clamped = Math.max(0, Math.min(100, score));
  const stroke = Math.max(3, Math.round(size / 10));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;
  return (
    <svg
      className="score-ring"
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={`Match score ${clamped} out of 100: ${style.label.toLowerCase()}`}
    >
      <circle cx={center} cy={center} r={radius} fill="none" stroke="#e3e3dc" strokeWidth={stroke} />
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={style.color}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={`${(clamped / 100) * circumference} ${circumference}`}
        transform={`rotate(-90 ${center} ${center})`}
      />
      <text
        x={center}
        y={center}
        textAnchor="middle"
        dominantBaseline="central"
        className="score-ring-value"
        style={{ fontSize: `${Math.round(size * 0.36)}px` }}
      >
        {clamped}
      </text>
    </svg>
  );
}
