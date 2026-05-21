"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import {
  fetchStages, fetchIssues,
  type Stage, type Issue, type StagesResponse, type IssuesResponse,
} from "@/lib/api";
import { GlobalFilter, type FilterState } from "@/components/GlobalFilter";
import { IssueTimelineModal } from "@/components/IssueTimelineModal";
import { SectionCard } from "@/components/SectionCard";
import { Spinner } from "@/components/Spinner";
import { STAGE_LABELS, STAGE_COLOR, STAGE_ORDER } from "@/lib/labels";
import { formatDays, formatCount, riskEmoji } from "@/lib/format";

const PAGE_SIZE = 50;

export default function FlowPage() {
  const [filter, setFilter] = useState<FilterState>({ projectId: null, periodMonths: 6 });
  const [selectedStage, setSelectedStage] = useState<string | null>(null);
  const [stagesData, setStagesData] = useState<StagesResponse | null>(null);
  const [issuesData, setIssuesData] = useState<IssuesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [issuesLoading, setIssuesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);

  // 펀넬 데이터 로드
  useEffect(() => {
    setLoading(true);
    fetchStages({ project_id: filter.projectId ?? undefined, period_months: filter.periodMonths })
      .then(setStagesData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filter]);

  // 이슈 목록 로드
  const loadIssues = useCallback((stage: string | null, f: FilterState) => {
    setIssuesLoading(true);
    fetchIssues({
      project_id: f.projectId ?? undefined,
      period_months: f.periodMonths,
      flow_stage: stage ?? undefined,
      sort_by: "days_in_stage",
      limit: PAGE_SIZE,
    })
      .then(setIssuesData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setIssuesLoading(false));
  }, []);

  useEffect(() => {
    loadIssues(selectedStage, filter);
  }, [filter, selectedStage, loadIssues]);

  const handleFilterChange = (next: Partial<FilterState>) =>
    setFilter((prev) => ({ ...prev, ...next }));

  const handleStageClick = (stage: string) =>
    setSelectedStage((prev) => (prev === stage ? null : stage));

  // 펀넬 단계 표시 (done 제외)
  const displayStages = STAGE_ORDER.filter((s) => s !== "done");
  const stageMap = Object.fromEntries(
    (stagesData?.stages ?? []).map((s) => [s.stage, s])
  );

  return (
    <div className="p-6 space-y-5 max-w-7xl">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold" style={{ color: "var(--foreground)" }}>
          흐름 진단
        </h1>
        <GlobalFilter filter={filter} onChange={handleFilterChange} />
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

      {/* 펀넬 */}
      <SectionCard
        title="단계별 현황"
        badge={
          stagesData && (
            <span className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: "var(--color-good)20", color: "var(--color-good)" }}>
              주간 완료 {stagesData.weekly_throughput}건
            </span>
          )
        }
      >
        {loading ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : (
          <div className="grid grid-cols-4 gap-3">
            {displayStages.map((stageKey) => {
              const s: Stage | undefined = stageMap[stageKey];
              const active = selectedStage === stageKey;
              const color = STAGE_COLOR[stageKey];
              const count = s?.issue_count ?? 0;
              const avgDays = s?.avg_days_in_stage ?? 0;

              return (
                <button
                  key={stageKey}
                  onClick={() => handleStageClick(stageKey)}
                  className="flex flex-col gap-2 p-4 rounded-xl text-left transition-all"
                  style={{
                    backgroundColor: active ? color + "18" : "var(--background)",
                    border: `1.5px solid ${active ? color : "var(--border)"}`,
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className="text-xs font-medium px-2 py-0.5 rounded-full"
                      style={{ backgroundColor: color + "20", color }}
                    >
                      {STAGE_LABELS[stageKey]}
                    </span>
                    {s?.high_risk_count ? (
                      <span className="text-xs font-medium" style={{ color: "var(--color-critical)" }}>
                        🔴 {s.high_risk_count}
                      </span>
                    ) : null}
                  </div>
                  <div>
                    <div className="text-2xl font-bold" style={{ color: "var(--foreground)" }}>
                      {count.toLocaleString()}
                      <span className="text-sm font-normal ml-1" style={{ color: "var(--muted)" }}>건</span>
                    </div>
                    <div className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                      평균 {formatDays(avgDays)} 체류
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </SectionCard>

      {/* 이슈 목록 */}
      <SectionCard
        title={selectedStage ? `${STAGE_LABELS[selectedStage]} 이슈` : "전체 이슈"}
        badge={
          issuesData && (
            <span className="text-xs" style={{ color: "var(--muted)" }}>
              총 {issuesData.total.toLocaleString()}건
            </span>
          )
        }
      >
        {issuesLoading ? (
          <div className="flex justify-center py-6"><Spinner /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["#", "제목", "단계", "담당자", "체류일", "전체", "위험"].map((h) => (
                    <th
                      key={h}
                      className="px-3 py-2 text-left text-xs font-medium"
                      style={{ color: "var(--muted)" }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {issuesData?.issues.map((issue) => (
                  <tr
                    key={issue.issue_id}
                    onClick={() => setSelectedIssue(issue)}
                    className="cursor-pointer hover:opacity-80 transition-opacity"
                    style={{ borderBottom: "1px solid var(--border)" }}
                  >
                    <td className="px-3 py-2.5" style={{ color: "var(--muted)" }}>
                      {issue.issue_id}
                    </td>
                    <td className="px-3 py-2.5 max-w-xs">
                      <span
                        className="block truncate font-medium"
                        style={{ color: "var(--foreground)" }}
                        title={issue.subject}
                      >
                        {issue.subject}
                      </span>
                      {issue.is_rework && (
                        <span className="text-xs" style={{ color: "var(--color-warning)" }}>재작업</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      <span
                        className="text-xs px-1.5 py-0.5 rounded-full"
                        style={{
                          backgroundColor: (STAGE_COLOR[issue.flow_stage] ?? "var(--color-normal)") + "20",
                          color: STAGE_COLOR[issue.flow_stage] ?? "var(--color-normal)",
                        }}
                      >
                        {STAGE_LABELS[issue.flow_stage] ?? issue.flow_stage}
                      </span>
                    </td>
                    <td className="px-3 py-2.5" style={{ color: "var(--foreground)" }}>
                      {issue.assignee_name ?? "—"}
                    </td>
                    <td className="px-3 py-2.5 font-medium" style={{ color: "var(--foreground)" }}>
                      {formatDays(issue.days_in_stage)}
                    </td>
                    <td className="px-3 py-2.5" style={{ color: "var(--muted)" }}>
                      {formatDays(issue.total_days)}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="font-medium">
                        {riskEmoji(issue.risk_score)} {issue.risk_score}
                      </span>
                    </td>
                  </tr>
                ))}
                {!issuesLoading && issuesData?.issues.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-3 py-8 text-center text-sm"
                      style={{ color: "var(--muted)" }}
                    >
                      데이터가 없습니다. Settings에서 Redmine 동기화를 실행하세요.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      {/* 타임라인 모달 */}
      <IssueTimelineModal issue={selectedIssue} onClose={() => setSelectedIssue(null)} />
    </div>
  );
}
