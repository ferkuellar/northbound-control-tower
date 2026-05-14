import { ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3, ClipboardList, Database, Gauge, ShieldAlert } from "lucide-react";

import { SectionCard } from "@/components/dashboard/SectionCard";
import { getScoreColor, ScoreGauge } from "@/components/dashboard/ScoreGauge";
import type { DimensionScore, ScoreTrend } from "@/types/dashboard";

const icons = {
  overall: Gauge,
  finops: BarChart3,
  governance: ClipboardList,
  observability: Database,
  security_baseline: ShieldAlert,
  resilience: Gauge,
};

function trendMeta(trend: ScoreTrend): { label: string; className: string; icon: typeof ArrowRight } {
  if (trend === "improving") return { label: "Improving", className: "text-[#1D9E75]", icon: ArrowUpRight };
  if (trend === "declining" || trend === "degrading") return { label: "Degrading", className: "text-[#A32D2D]", icon: ArrowDownRight };
  if (trend === "stable") return { label: "Stable", className: "text-northbound-textMuted", icon: ArrowRight };
  return { label: "Unknown", className: "text-northbound-muted", icon: ArrowRight };
}

export function ScoreCard({ score }: { score: DimensionScore }) {
  const Icon = icons[score.key as keyof typeof icons] ?? Gauge;
  const trend = trendMeta(score.trend);
  const TrendIcon = trend.icon;
  const scoreColor = getScoreColor(score.label_text);

  return (
    <SectionCard className="border-t-2 p-3 text-center" style={{ borderTopColor: scoreColor }}>
      <div className="mb-1 flex items-center justify-center gap-1.5 text-xs text-northbound-textMuted">
        <Icon size={14} aria-hidden="true" />
        <span>{score.label}</span>
      </div>
      <div className="flex justify-center">
        <ScoreGauge score={score.score} label={score.label_text} title={score.label} />
      </div>
      <div className={`mt-1 inline-flex items-center gap-1 text-xs font-medium ${trend.className}`}>
        <TrendIcon size={13} aria-hidden="true" />
        {trend.label}
      </div>
      {score.top_driver ? <p className="mt-2 line-clamp-2 text-[11px] leading-5 text-northbound-textMuted">{score.top_driver}</p> : null}
    </SectionCard>
  );
}
