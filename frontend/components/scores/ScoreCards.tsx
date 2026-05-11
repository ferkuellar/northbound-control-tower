import { MetricCard } from "@/components/dashboard/MetricCard";
import { scoreByType, scoreLabels } from "@/lib/formatters";
import type { CloudScore, ScoreSummary } from "@/lib/types";

type ScoreCardsProps = {
  scores: CloudScore[];
  summary: ScoreSummary;
};

const scoreOrder = ["overall", "finops", "governance", "observability", "security_baseline", "resilience"];

export function ScoreCards({ scores, summary }: ScoreCardsProps) {
  const byType = scoreByType(scores);

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {scoreOrder.map((scoreType) => {
        const score = byType.get(scoreType);
        const value = score?.score_value ?? (scoreType === "overall" ? summary.overall_score : summary.domain_scores[scoreType]);
        return (
          <MetricCard
            key={scoreType}
            label={scoreLabels[scoreType] ?? scoreType}
            value={value ?? "N/A"}
            grade={score?.grade ?? summary.grades[scoreType]}
            trend={score?.trend ?? summary.trends[scoreType]}
            summary={score?.summary}
          />
        );
      })}
    </div>
  );
}
