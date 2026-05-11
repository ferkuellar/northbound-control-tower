import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Card, CardContent } from "@/components/ui/Card";
import { labelize } from "@/lib/formatters";

type MetricCardProps = {
  label: string;
  value: string | number;
  grade?: string;
  trend?: string;
  summary?: string;
};

function trendIcon(trend: string | undefined) {
  if (trend === "improving") {
    return <ArrowUpRight size={16} aria-hidden="true" />;
  }
  if (trend === "degrading") {
    return <ArrowDownRight size={16} aria-hidden="true" />;
  }
  return <ArrowRight size={16} aria-hidden="true" />;
}

function toneForGrade(grade: string | undefined): "success" | "warning" | "danger" | "neutral" {
  if (grade === "excellent" || grade === "good") {
    return "success";
  }
  if (grade === "fair") {
    return "warning";
  }
  if (grade === "poor" || grade === "critical") {
    return "danger";
  }
  return "neutral";
}

export function MetricCard({ label, value, grade, trend, summary }: MetricCardProps) {
  return (
    <Card>
      <CardContent className="space-y-4">
        <div className="flex items-start justify-between gap-3">
          <p className="text-sm font-medium text-steel">{label}</p>
          {grade ? <Badge tone={toneForGrade(grade)}>{labelize(grade)}</Badge> : null}
        </div>
        <div>
          <p className="text-3xl font-semibold tracking-normal text-ink">{value}</p>
          {trend ? (
            <p className="mt-2 inline-flex items-center gap-1 text-sm text-steel">
              {trendIcon(trend)}
              {labelize(trend)}
            </p>
          ) : null}
        </div>
        {summary ? <p className="line-clamp-2 min-h-10 text-sm text-steel">{summary}</p> : null}
      </CardContent>
    </Card>
  );
}
