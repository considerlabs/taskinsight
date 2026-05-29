"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { fetchInsightCards, type InsightCard, type InsightCardsResponse } from "@/lib/api";
import { GlobalFilter, type FilterState } from "@/components/GlobalFilter";
import { InsightCard as InsightCardComponent } from "@/components/InsightCard";
import { InsightDrilldown } from "@/components/InsightDrilldown";
import { Spinner } from "@/components/Spinner";

const ZONE_META = {
  alert:      { label: "즉시 확인 필요", color: "var(--color-critical)",  dot: "🔴" },
  monitoring: { label: "모니터링",       color: "var(--color-normal)",    dot: "⚪" },
  disabled:   { label: "비활성화",       color: "var(--muted)",           dot: "⏸" },
} as const;

export default function InsightsPage() {
  const [filter, setFilter] = useState<FilterState>({ projectId: null, periodMonths: 6 });
  const [data, setData] = useState<InsightCardsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drillCard, setDrillCard] = useState<InsightCard | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchInsightCards({
      project_id: filter.projectId ?? undefined,
      period_months: filter.periodMonths,
    })
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filter]);

  const byZone = (zone: "alert" | "monitoring" | "disabled"): InsightCard[] =>
    (data?.cards ?? []).filter((c) => c.zone === zone);

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold" style={{ color: "var(--foreground)" }}>
            인사이트
          </h1>
          {data && (
            <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
              카드 {data.cards.length}종 · 즉시 확인 {data.alert_count}건
              {data.generated_at && (
                <span className="ml-2">
                  · 갱신 {new Date(data.generated_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}
                </span>
              )}
            </p>
          )}
        </div>
        <GlobalFilter filter={filter} onChange={(next) => setFilter((p) => ({ ...p, ...next }))} />
      </div>

      {error && (
        <div
          className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm"
          style={{ backgroundColor: "var(--color-critical)15", color: "var(--color-critical)" }}
        >
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : (
        <>
          {/* 데이터 상태 범례 */}
          <div
            className="flex items-center gap-4 px-4 py-2.5 rounded-xl text-xs"
            style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
          >
            <span style={{ color: "var(--muted)" }}>데이터 상태:</span>
            {[
              { key: "실측",     color: "var(--color-good)" },
              { key: "근사치",   color: "var(--color-warning)" },
              { key: "수집예정", color: "var(--color-normal)" },
              { key: "비활성",   color: "var(--color-normal)" },
            ].map(({ key, color }) => (
              <span key={key} className="flex items-center gap-1">
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span style={{ color: "var(--foreground)" }}>{key}</span>
              </span>
            ))}
          </div>

          {/* 존별 렌더링 */}
          {(["alert", "monitoring", "disabled"] as const).map((zone) => {
            const cards = byZone(zone);
            if (cards.length === 0) return null;
            const meta = ZONE_META[zone];
            return (
              <section key={zone}>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-base">{meta.dot}</span>
                  <h2
                    className="text-sm font-semibold"
                    style={{ color: zone === "alert" ? "var(--color-critical)" : "var(--foreground)" }}
                  >
                    {meta.label}
                  </h2>
                  <span
                    className="text-xs px-2 py-0.5 rounded-full"
                    style={{ backgroundColor: "var(--background)", color: "var(--muted)", border: "1px solid var(--border)" }}
                  >
                    {cards.length}
                  </span>
                  {zone === "alert" && (
                    <span
                      className="text-xs px-2 py-0.5 rounded-full"
                      style={{ backgroundColor: "var(--color-critical)15", color: "var(--color-critical)" }}
                    >
                      즉시 조치 권장
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {cards.map((card) => (
                    <InsightCardComponent key={card.id} card={card} onClick={setDrillCard} />
                  ))}
                </div>
              </section>
            );
          })}

          <InsightDrilldown
            card={drillCard}
            projectId={filter.projectId ?? undefined}
            onClose={() => setDrillCard(null)}
          />

          {data && data.cards.length === 0 && (
            <div className="flex flex-col items-center gap-3 py-16">
              <RefreshCw size={32} style={{ color: "var(--muted)" }} />
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                데이터가 없습니다. Settings에서 Redmine 동기화를 실행하세요.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
