"use client";

import type { EChartsOption } from "echarts";

import { ChartPanel } from "@/components/dashboard/ChartPanel";
import { labelize, scoreLabels } from "@/lib/formatters";
import type { CloudScore, FindingSummary, ScoreSummary } from "@/lib/types";

type ScoreChartsProps = {
  summary: ScoreSummary;
  history: CloudScore[];
  findingsSummary: FindingSummary;
};

export function ScoreCharts({ summary, history, findingsSummary }: ScoreChartsProps) {
  const domainEntries = Object.entries(summary.domain_scores);
  const domainOption: EChartsOption | null = domainEntries.length
    ? {
        grid: { left: 24, right: 24, top: 20, bottom: 48, containLabel: true },
        xAxis: { type: "category", data: domainEntries.map(([key]) => scoreLabels[key] ?? labelize(key)), axisLabel: { rotate: 20 } },
        yAxis: { type: "value", min: 0, max: 100 },
        series: [{ type: "bar", data: domainEntries.map(([, value]) => value), itemStyle: { color: "#0F766E" } }],
        tooltip: { trigger: "axis" },
      }
    : null;

  const sortedHistory = [...history].sort(
    (left, right) => new Date(left.calculated_at).getTime() - new Date(right.calculated_at).getTime(),
  );
  const historyOption: EChartsOption | null = sortedHistory.length
    ? {
        grid: { left: 32, right: 24, top: 20, bottom: 44, containLabel: true },
        xAxis: { type: "category", data: sortedHistory.map((score) => new Date(score.calculated_at).toLocaleDateString()) },
        yAxis: { type: "value", min: 0, max: 100 },
        series: [
          {
            type: "line",
            smooth: true,
            data: sortedHistory.map((score) => score.score_value),
            lineStyle: { color: "#0F766E", width: 3 },
            itemStyle: { color: "#0F766E" },
          },
        ],
        tooltip: { trigger: "axis" },
      }
    : null;

  const severityEntries = Object.entries(findingsSummary.by_severity);
  const severityOption: EChartsOption | null = severityEntries.length
    ? {
        tooltip: { trigger: "item" },
        series: [
          {
            type: "pie",
            radius: ["45%", "70%"],
            data: severityEntries.map(([name, value]) => ({ name: labelize(name), value })),
            color: ["#B42318", "#DC6803", "#D97706", "#0F766E", "#455A64"],
          },
        ],
      }
    : null;

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <ChartPanel title="Domain Scores" option={domainOption} />
      <ChartPanel title="Score History" option={historyOption} />
      <ChartPanel title="Severity Distribution" option={severityOption} />
    </div>
  );
}
