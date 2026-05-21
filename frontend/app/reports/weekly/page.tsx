"use client";

import { useEffect, useState } from "react";
import { RefreshCw, Bot, History } from "lucide-react";
import { fetchLatestReport, generateReport, type WeeklyReport } from "@/lib/api";
import { SectionCard } from "@/components/SectionCard";
import { Spinner } from "@/components/Spinner";
import { STAGE_LABELS } from "@/lib/labels";
import { deltaMark, formatDate, formatDateTime } from "@/lib/format";

export default function WeeklyReportPage() {
  const [report, setReport] = useState<WeeklyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const loadLatest = () => {
    setLoading(true);
    setNotFound(false);
    fetchLatestReport()
      .then(setReport)
      .catch((e: Error) => {
        if (e.message.includes("404")) setNotFound(true);
        else setError(e.message);
      })
      .finally(() => setLoading(false));
  };

  useEffect(loadLatest, []);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const newReport = await generateReport();
      setReport(newReport);
      setNotFound(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold" style={{ color: "var(--foreground)" }}>주간보고</h1>
          {report && (
            <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
              {formatDate(report.period_start)} ~ {formatDate(report.period_end)}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {report && (
            <button
              onClick={loadLatest}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-opacity hover:opacity-70"
              style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
            >
              <History size={13} />
              이전 보고서
            </button>
          )}
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-opacity hover:opacity-80 disabled:opacity-50"
            style={{ backgroundColor: "var(--color-accent)", color: "#fff" }}
          >
            {generating ? <Spinner size={15} /> : <RefreshCw size={15} />}
            이번 주 보고서 생성
          </button>
        </div>
      </div>

      {error && (
        <p className="text-sm px-4 py-3 rounded-xl" style={{ color: "var(--color-critical)", backgroundColor: "var(--color-critical)15" }}>
          {error}
        </p>
      )}

      {/* 로딩 */}
      {(loading || generating) && (
        <div className="flex flex-col items-center gap-3 py-16">
          <Spinner size={32} />
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            {generating ? "LLM이 보고서를 작성 중입니다… (최대 2분)" : "불러오는 중…"}
          </p>
        </div>
      )}

      {/* 아직 없음 */}
      {!loading && !generating && notFound && (
        <div
          className="flex flex-col items-center gap-4 py-16 rounded-2xl"
          style={{ border: "1px dashed var(--border)" }}
        >
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            생성된 보고서가 없습니다.
          </p>
          <button
            onClick={handleGenerate}
            className="px-5 py-2 rounded-lg text-sm font-medium"
            style={{ backgroundColor: "var(--color-accent)", color: "#fff" }}
          >
            첫 보고서 생성하기
          </button>
        </div>
      )}

      {/* 보고서 본문 */}
      {!loading && !generating && report && (
        <div className="space-y-4">
          {/* 1. 이번 주 완료량 */}
          <SectionCard title="1. 이번 주 완료량">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-3xl font-bold" style={{ color: "var(--foreground)" }}>
                {report.throughput.current}건
              </span>
              <span
                className="text-sm font-medium"
                style={{
                  color: report.throughput.delta >= 0 ? "var(--color-good)" : "var(--color-critical)",
                }}
              >
                {deltaMark(report.throughput.delta)} (지난 주 {report.throughput.previous}건 대비)
              </span>
            </div>
            {report.narrative_text && <NarrativeBlock text={extractSection(report.narrative_text, 0)} />}
          </SectionCard>

          {/* 2. 정체 구간 */}
          <SectionCard title="2. 정체 구간 현황">
            <div className="space-y-2 mb-3">
              {report.bottleneck?.map((b, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between px-3 py-2 rounded-lg"
                  style={{
                    backgroundColor: i === 0 ? "var(--color-critical)10" : "var(--background)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div className="flex items-center gap-2">
                    <span style={{ color: i === 0 ? "var(--color-critical)" : "var(--color-warning)" }}>
                      {i === 0 ? "🔴" : "🟠"}
                    </span>
                    <span className="text-sm font-medium" style={{ color: "var(--foreground)" }}>
                      {STAGE_LABELS[b.stage] ?? b.stage}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm" style={{ color: "var(--foreground)" }}>{b.count}건</span>
                    <span className="text-xs ml-2" style={{ color: "var(--muted)" }}>
                      평균 {b.avg_days.toFixed(0)}일
                    </span>
                  </div>
                </div>
              ))}
            </div>
            {report.narrative_text && <NarrativeBlock text={extractSection(report.narrative_text, 1)} />}
          </SectionCard>

          {/* 3. 완료 예측 */}
          <SectionCard title="3. 완료 예측 변화">
            <div className="flex gap-4 mb-3">
              {[
                { label: "P50 (보통)", weeks: report.forecast?.p50_weeks },
                { label: "P85 (보수적)", weeks: report.forecast?.p85_weeks },
                { label: "P95 (안전)", weeks: report.forecast?.p95_weeks },
              ].map(({ label, weeks }) => (
                <div
                  key={label}
                  className="flex-1 flex flex-col gap-0.5 px-3 py-2 rounded-lg"
                  style={{ backgroundColor: "var(--background)", border: "1px solid var(--border)" }}
                >
                  <span className="text-xs" style={{ color: "var(--muted)" }}>{label}</span>
                  <span className="text-lg font-bold" style={{ color: "var(--foreground)" }}>
                    {weeks ?? "—"}주
                  </span>
                </div>
              ))}
            </div>
            {report.narrative_text && <NarrativeBlock text={extractSection(report.narrative_text, 2)} />}
          </SectionCard>

          {/* 생성 시각 */}
          <p className="text-xs text-right" style={{ color: "var(--muted)" }}>
            생성 시각: {formatDateTime(report.generated_at)}
          </p>
        </div>
      )}
    </div>
  );
}

// LLM 서술 단락 추출 (개행 또는 번호 기준)
function extractSection(text: string, index: number): string {
  if (!text) return "";
  const lines = text.split(/\n+/).filter((l) => l.trim());
  return lines[index] ?? (index === 0 ? text : "");
}

function NarrativeBlock({ text }: { text: string }) {
  if (!text) return null;
  return (
    <div
      className="flex items-start gap-2 mt-2 p-3 rounded-lg"
      style={{ backgroundColor: "var(--color-accent)08", border: "1px solid var(--color-accent)25" }}
    >
      <Bot size={14} className="shrink-0 mt-0.5" style={{ color: "var(--color-accent)" }} />
      <p className="text-sm leading-relaxed" style={{ color: "var(--foreground)", opacity: 0.85 }}>
        {text}
      </p>
    </div>
  );
}
