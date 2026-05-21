"use client";

import { useEffect, useState } from "react";
import { fetchDashboard, type DashboardSummary } from "@/lib/api";
import { GlobalFilter, type FilterState } from "@/components/GlobalFilter";
import { MetricCard } from "@/components/MetricCard";
import { SectionCard } from "@/components/SectionCard";
import { Spinner } from "@/components/Spinner";
import { deltaMark, formatDays } from "@/lib/format";

export default function DashboardPage() {
  const [filter, setFilter] = useState<FilterState>({ projectId: null, periodMonths: 6 });
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchDashboard(filter.projectId ?? undefined)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filter]);

  const handleFilterChange = (next: Partial<FilterState>) =>
    setFilter((prev) => ({ ...prev, ...next }));

  return (
    <div className="p-6 space-y-5 max-w-7xl">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold" style={{ color: "var(--foreground)" }}>Dashboard</h1>
        <GlobalFilter filter={filter} onChange={handleFilterChange} />
      </div>

      {error && (
        <p className="text-sm px-4 py-3 rounded-xl" style={{ color: "var(--color-critical)", backgroundColor: "var(--color-critical)15" }}>
          {error}
        </p>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size={32} /></div>
      ) : data ? (
        <div className="space-y-4">
          {/* Speed */}
          <SectionCard title="Speed — 속도">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <MetricCard
                label="전체 소요일 (평균)"
                value={formatDays(data.speed.avg_lead_time_days)}
                accent="normal"
              />
              <MetricCard
                label="주간 완료량"
                value={`${data.speed.weekly_throughput}건`}
                sub={deltaMark(data.speed.throughput_delta) + " vs 전주"}
                accent={data.speed.throughput_delta >= 0 ? "good" : "warning"}
              />
              <MetricCard
                label="완료 예측 (P50)"
                value={data.speed.forecast_p50_weeks != null ? `${data.speed.forecast_p50_weeks}주` : "—"}
                sub="보통 시나리오"
                accent="accent"
              />
              <MetricCard
                label="잔여 이슈"
                value={`${data.speed.backlog_count.toLocaleString()}건`}
                accent="normal"
              />
            </div>
          </SectionCard>

          {/* Effectiveness */}
          <SectionCard title="Effectiveness — 효율">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <MetricCard
                label="쏠림 지수 (Gini)"
                value={data.effectiveness.gini_index.toFixed(2)}
                sub={data.effectiveness.gini_index > 0.5 ? "높음 — 집중 주의" : "정상"}
                accent={data.effectiveness.gini_index > 0.5 ? "critical" : "good"}
              />
              <MetricCard
                label="진행 중 업무 (WIP)"
                value={`${data.effectiveness.total_wip.toLocaleString()}건`}
                accent="normal"
              />
              <MetricCard
                label="미할당 이슈"
                value={`${data.effectiveness.unassigned}건`}
                accent={data.effectiveness.unassigned > 0 ? "warning" : "good"}
              />
              <MetricCard
                label="상위 3명 WIP 비율"
                value={`${(data.effectiveness.top3_wip_ratio * 100).toFixed(0)}%`}
                sub={data.effectiveness.top3_wip_ratio > 0.5 ? "집중 심함" : "양호"}
                accent={data.effectiveness.top3_wip_ratio > 0.5 ? "warning" : "good"}
              />
            </div>
          </SectionCard>

          {/* Quality */}
          <SectionCard title="Quality — 품질">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <MetricCard
                label="재작업 건수"
                value={`${data.quality.rework_count}건`}
                sub={`전체의 ${(data.quality.rework_rate * 100).toFixed(1)}%`}
                accent={data.quality.rework_rate > 0.1 ? "warning" : "good"}
              />
              <MetricCard
                label="이상 신호"
                value={`${data.quality.anomaly_count}건`}
                sub="장기 체류 또는 위험점수 80+"
                accent={data.quality.anomaly_count > 0 ? "critical" : "good"}
              />
              <MetricCard
                label="극단 이슈"
                value={`${data.quality.extreme_count}건`}
                sub="1,000일 이상 체류"
                accent={data.quality.extreme_count > 0 ? "critical" : "normal"}
              />
              <MetricCard
                label="전체 이슈"
                value={`${data.quality.total_issues.toLocaleString()}건`}
                accent="normal"
              />
            </div>
          </SectionCard>
        </div>
      ) : null}
    </div>
  );
}
