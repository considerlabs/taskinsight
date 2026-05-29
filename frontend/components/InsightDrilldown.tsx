"use client";

import { useEffect, useState, useCallback } from "react";
import { X, ChevronLeft, ChevronRight } from "lucide-react";
import {
  fetchInsightCardIssues,
  type InsightCard,
  type InsightDrilldownIssue,
} from "@/lib/api";
import { Spinner } from "@/components/Spinner";
import { STAGE_LABELS, STAGE_COLOR } from "@/lib/labels";
import { formatDays } from "@/lib/format";

const PAGE_SIZE = 50;

interface Props {
  card: InsightCard | null;
  projectId?: number;
  onClose: () => void;
}

export function InsightDrilldown({ card, projectId, onClose }: Props) {
  const [issues, setIssues] = useState<InsightDrilldownIssue[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const load = useCallback(
    (cardId: string, off: number) => {
      setLoading(true);
      setError(null);
      fetchInsightCardIssues(cardId, { project_id: projectId, limit: PAGE_SIZE, offset: off })
        .then((res) => {
          setIssues(res.issues);
          setTotal(res.total);
          setNote(res.note ?? null);
        })
        .catch((e: Error) => setError(e.message))
        .finally(() => setLoading(false));
    },
    [projectId],
  );

  useEffect(() => {
    if (!card) return;
    setOffset(0);
    setIssues([]);
    load(card.id, 0);
  }, [card?.id, load]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  if (!card) return null;

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const handlePage = (dir: 1 | -1) => {
    const next = offset + dir * PAGE_SIZE;
    setOffset(next);
    load(card.id, next);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: "rgba(0,0,0,0.6)" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="w-full max-w-4xl max-h-[85vh] flex flex-col rounded-2xl overflow-hidden"
        style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
      >
        {/* 헤더 */}
        <div
          className="flex items-center justify-between px-5 py-4 shrink-0"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <div>
            <div className="text-xs font-mono mb-0.5" style={{ color: "var(--muted)" }}>
              {card.id}
            </div>
            <h2 className="text-base font-semibold" style={{ color: "var(--foreground)" }}>
              {card.title}
            </h2>
          </div>
          <div className="flex items-center gap-3">
            {total > 0 && (
              <span className="text-sm" style={{ color: "var(--muted)" }}>
                총 {total.toLocaleString()}건
              </span>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:opacity-70 transition-opacity"
              style={{ color: "var(--muted)" }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* 본문 */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex justify-center py-12">
              <Spinner />
            </div>
          ) : error ? (
            <div className="px-5 py-8 text-sm text-center" style={{ color: "var(--color-critical)" }}>
              {error}
            </div>
          ) : note && issues.length === 0 ? (
            <div className="px-5 py-12 text-sm text-center" style={{ color: "var(--muted)" }}>
              {note}
            </div>
          ) : issues.length === 0 ? (
            <div className="px-5 py-12 text-sm text-center" style={{ color: "var(--muted)" }}>
              해당 조건의 이슈가 없습니다
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["#", "제목", "단계", "프로젝트", "담당자", "단계 체류", "전체"].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-2.5 text-left text-xs font-medium"
                      style={{ color: "var(--muted)" }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {issues.map((issue) => (
                  <tr
                    key={issue.issue_id}
                    style={{ borderBottom: "1px solid var(--border)" }}
                    className="hover:opacity-80 transition-opacity"
                  >
                    <td className="px-4 py-2.5 text-xs" style={{ color: "var(--muted)" }}>
                      #{issue.issue_id}
                    </td>
                    <td className="px-4 py-2.5 max-w-xs">
                      <span
                        className="block truncate font-medium"
                        style={{ color: "var(--foreground)" }}
                        title={issue.subject}
                      >
                        {issue.subject}
                      </span>
                      {issue.is_rework && (
                        <span className="text-xs" style={{ color: "var(--color-warning)" }}>
                          재작업
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
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
                    <td className="px-4 py-2.5 text-xs" style={{ color: "var(--muted)" }}>
                      {issue.project_name ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-xs" style={{ color: "var(--foreground)" }}>
                      {issue.assignee_name ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 font-medium text-xs" style={{ color: "var(--foreground)" }}>
                      {formatDays(issue.days_in_stage)}
                    </td>
                    <td className="px-4 py-2.5 text-xs" style={{ color: "var(--muted)" }}>
                      {formatDays(issue.total_days)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* 페이지네이션 */}
        {totalPages > 1 && (
          <div
            className="flex items-center justify-between px-5 py-3 shrink-0"
            style={{ borderTop: "1px solid var(--border)" }}
          >
            <button
              onClick={() => handlePage(-1)}
              disabled={offset === 0}
              className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg disabled:opacity-30 transition-opacity"
              style={{ color: "var(--foreground)", border: "1px solid var(--border)" }}
            >
              <ChevronLeft size={14} /> 이전
            </button>
            <span className="text-xs" style={{ color: "var(--muted)" }}>
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => handlePage(1)}
              disabled={offset + PAGE_SIZE >= total}
              className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg disabled:opacity-30 transition-opacity"
              style={{ color: "var(--foreground)", border: "1px solid var(--border)" }}
            >
              다음 <ChevronRight size={14} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
