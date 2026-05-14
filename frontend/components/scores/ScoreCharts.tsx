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
  const axisText = "#BFC6D4";
  const gridLine = "rgba(224, 228, 235, 0.10)";
  const tooltipStyle = {
    backgroundColor: "#212631",
    borderColor: "#373F4E",
    textStyle: { color: "#FFFFFF" },
  };
  const domainOption: EChartsOption | null = domainEntries.length
    ? {
        grid: { left: 24, right: 24, top: 20, bottom: 48, containLabel: true },
        xAxis: {
          type: "category",
          data: domainEntries.map(([key]) => scoreLabels[key] ?? labelize(key)),
          axisLabel: { rotate: 20, color: axisText },
          axisLine: { lineStyle: { color: "#373F4E" } },
          axisTick: { lineStyle: { color: "#373F4E" } },
        },
        yAxis: {
          type: "value",
          min: 0,
          max: 100,
          axisLabel: { color: axisText },
          splitLine: { lineStyle: { color: gridLine } },
        },
        series: [{ type: "bar", data: domainEntries.map(([, value]) => value), itemStyle: { color: "#BFC6D4" } }],
        tooltip: { trigger: "axis", ...tooltipStyle },
      }
    : null;

  const sortedHistory = [...history].sort(
    (left, right) => new Date(left.calculated_at).getTime() - new Date(right.calculated_at).getTime(),
  );
  const historyOption: EChartsOption | null = sortedHistory.length
    ? {
        grid: { left: 32, right: 24, top: 20, bottom: 44, containLabel: true },
        xAxis: {
          type: "category",
          data: sortedHistory.map((score) => new Date(score.calculated_at).toLocaleDateString()),
          axisLabel: { color: axisText },
          axisLine: { lineStyle: { color: "#373F4E" } },
          axisTick: { lineStyle: { color: "#373F4E" } },
        },
        yAxis: {
          type: "value",
          min: 0,
          max: 100,
          axisLabel: { color: axisText },
          splitLine: { lineStyle: { color: gridLine } },
        },
        series: [
          {
            type: "line",
            smooth: true,
            data: sortedHistory.map((score) => score.score_value),
            lineStyle: { color: "#E0E4EB", width: 3 },
            itemStyle: { color: "#FFFFFF" },
          },
        ],
        tooltip: { trigger: "axis", ...tooltipStyle },
      }
    : null;

  const severityEntries = Object.entries(findingsSummary.by_severity);
  const severityOption: EChartsOption | null = severityEntries.length
    ? {
        tooltip: { trigger: "item", ...tooltipStyle },
        legend: { bottom: 0, textStyle: { color: axisText } },
        series: [
          {
            type: "pie",
            radius: ["45%", "70%"],
            data: severityEntries.map(([name, value]) => ({ name: labelize(name), value })),
            color: ["#991B1B", "#B45309", "#C2410C", "#047857", "#667085"],
            label: { color: axisText },
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
