import type { ScoreLabel } from "@/types/dashboard";

export function getScoreColor(label: ScoreLabel): string {
  if (label === "Excellent") return "#1D9E75";
  if (label === "Good") return "#BA7517";
  if (label === "Fair") return "#D85A30";
  return "#A32D2D";
}

type ScoreGaugeProps = {
  score: number;
  label: ScoreLabel;
  title: string;
};

export function ScoreGauge({ score, label, title }: ScoreGaugeProps) {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference * 0.75;
  const filled = arcLength * (Math.max(0, Math.min(100, score)) / 100);
  const color = getScoreColor(label);

  return (
    <svg viewBox="0 0 80 74" width="92" height="86" role="img" aria-label={`${title}: ${score} - ${label}`}>
      <circle
        cx="40"
        cy="42"
        r={radius}
        fill="none"
        stroke="#373F4E"
        strokeWidth="7"
        strokeDasharray={`${arcLength} ${circumference}`}
        transform="rotate(135 40 42)"
        strokeLinecap="round"
      />
      <circle
        cx="40"
        cy="42"
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth="7"
        strokeDasharray={`${filled} ${circumference}`}
        transform="rotate(135 40 42)"
        strokeLinecap="round"
      />
      <text x="40" y="39" textAnchor="middle" fontSize="18" fontWeight="600" fill="#FFFFFF">
        {score}
      </text>
      <text x="40" y="51" textAnchor="middle" fontSize="8.5" fontWeight="600" fill={color}>
        {label}
      </text>
    </svg>
  );
}
