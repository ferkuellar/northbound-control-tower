import { ScoreCard } from "@/components/dashboard/ScoreCard";
import type { ExecutiveDashboardData } from "@/types/dashboard";

export function ScoreGrid({ data }: { data: ExecutiveDashboardData }) {
  return (
    <div id="scores" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <ScoreCard score={data.overall_score} />
      {data.dimension_scores.map((score) => (
        <ScoreCard key={score.key} score={score} />
      ))}
    </div>
  );
}
