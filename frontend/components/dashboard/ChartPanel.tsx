"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";

import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";

type ChartPanelProps = {
  title: string;
  description?: string;
  option: EChartsOption | null;
  emptyTitle?: string;
};

export function ChartPanel({ title, description, option, emptyTitle = "No chart data available" }: ChartPanelProps) {
  const chartRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!chartRef.current || !option) {
      return undefined;
    }

    const chart = echarts.init(chartRef.current);
    chart.setOption(option);
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [option]);

  return (
    <Card>
      <CardHeader>
        <h3 className="text-base font-semibold text-ink">{title}</h3>
        {description ? <p className="mt-1 text-sm text-steel">{description}</p> : null}
      </CardHeader>
      <CardContent>
        {option ? <div ref={chartRef} className="h-72 w-full" /> : <EmptyState title={emptyTitle} />}
      </CardContent>
    </Card>
  );
}
