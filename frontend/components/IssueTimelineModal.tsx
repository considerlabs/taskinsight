"use client";

import { useEffect, useState } from "react";
import { X, ExternalLink, Bot, Clock } from "lucide-react";
import { fetchExplanation, type ExplanationResponse } from "@/lib/api";
import { Spinner } from "@/components/Spinner";
import { STAGE_LABELS, STAGE_COLOR } from "@/lib/labels";
import { formatDays, riskEmoji } from "@/lib/format";
import type { Issue } from "@/lib/api";

const REDMINE_BASE = process.env.NEXT_PUBLIC_REDMINE_URL ?? "http://redmine.mannaplanet.co.kr:5555/redmine";

interface IssueTimelineModalProps {
  issue: Issue | null;
  onClose: () => void;
}

export function IssueTimelineModal({ issue, onClose }: IssueTimelineModalProps) {
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!issue) return;
    setExplanation(null);
    setError(null);
    setLoading(true);
    fetchExplanation(issue.issue_id)
      .then(setExplanation)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [issue?.issue_id]);

  // ESC 닫기
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  if (!issue) return null;

  const stageColor = STAGE_COLOR[issue.flow_stage] ?? "var(--color-normal)";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: "rgba(0,0,0,0.5)" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="relative w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl shadow-xl"
        style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
      >
        {/* 헤더 */}
        <div
          className="sticky top-0 flex items-start justify-between gap-3 px-6 py-4 rounded-t-2xl"
          style={{ backgroundColor: "var(--surface)", borderBottom: "1px solid var(--border)" }}
        >
          <div className="flex flex-col gap-1 min-w-0">
            <div className="flex items-center gap-2">
              <span
                className="text-xs font-medium px-2 py-0.5 rounded-full"
                style={{ backgroundColor: stageColor + "20", color: stageColor }}
              >
                {STAGE_LABELS[issue.flow_stage] ?? issue.flow_stage}
              </span>
              <span className="text-xs" style={{ color: "var(--muted)" }}>
                #{issue.issue_id}
              </span>
              <span className="text-lg">{riskEmoji(issue.risk_score)}</span>
            </div>
            <h2
              className="text-base font-semibold leading-snug"
              style={{ color: "var(--foreground)" }}
            >
              {issue.subject}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 p-1.5 rounded-lg hover:opacity-70 transition-opacity"
            style={{ color: "var(--muted)" }}
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* 요약 메타 */}
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-1.5" style={{ color: "var(--muted)" }}>
              <Clock size={14} />
              <span>현재 단계 체류 <strong style={{ color: "var(--foreground)" }}>{formatDays(issue.days_in_stage)}</strong></span>
            </div>
            <div className="flex items-center gap-1.5" style={{ color: "var(--muted)" }}>
              <span>전체 소요 <strong style={{ color: "var(--foreground)" }}>{formatDays(issue.total_days)}</strong></span>
            </div>
            {issue.assignee_name && (
              <div style={{ color: "var(--muted)" }}>
                담당자 <strong style={{ color: "var(--foreground)" }}>{issue.assignee_name}</strong>
              </div>
            )}
            {issue.is_rework && (
              <span
                className="text-xs px-2 py-0.5 rounded-full font-medium"
                style={{ backgroundColor: "var(--color-warning)20", color: "var(--color-warning)" }}
              >
                재작업
              </span>
            )}
          </div>

          {/* LLM 분석 */}
          <div
            className="rounded-xl p-4"
            style={{ backgroundColor: "var(--background)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-center gap-2 mb-3">
              <Bot size={16} style={{ color: "var(--color-accent)" }} />
              <span className="text-xs font-medium" style={{ color: "var(--color-accent)" }}>
                TaskInsight 분석
              </span>
              {explanation && (
                <span className="text-xs" style={{ color: "var(--muted)" }}>
                  · {explanation.model_version} · {explanation.cached ? "캐시" : "방금 생성"}
                </span>
              )}
            </div>

            {loading && (
              <div className="flex items-center gap-2" style={{ color: "var(--muted)" }}>
                <Spinner size={16} />
                <span className="text-sm">분석 중… (최대 30초)</span>
              </div>
            )}
            {error && (
              <p className="text-sm" style={{ color: "var(--color-critical)" }}>
                분석 불가: {error}
              </p>
            )}
            {explanation && !loading && (
              <p className="text-sm leading-relaxed" style={{ color: "var(--foreground)" }}>
                {explanation.explanation}
              </p>
            )}
          </div>

          {/* Redmine 링크 */}
          <div className="flex justify-end">
            <a
              href={`${REDMINE_BASE}/issues/${issue.issue_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm font-medium hover:opacity-70 transition-opacity"
              style={{ color: "var(--color-accent)" }}
            >
              Redmine에서 열기
              <ExternalLink size={14} />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
