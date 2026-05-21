/** TaskInsight 한국어 용어 사전 (스펙 11장) */

export const STAGE_LABELS: Record<string, string> = {
  backlog:     "대기 중",
  in_progress: "진행 중",
  review:      "검수 중",
  done:        "완료",
  blocked:     "보류됨",
};

export const STAGE_ORDER = ["backlog", "in_progress", "review", "blocked", "done"] as const;
export type FlowStage = (typeof STAGE_ORDER)[number];

export const METRIC_LABELS = {
  cycle_time:       "처리 기간",
  lead_time:        "전체 소요일",
  queue_time:       "대기 기간",
  review_wait:      "검수 대기",
  wip:              "진행 중 업무",
  throughput:       "주간 완료량",
  forecast:         "완료 예측",
  risk:             "지연 위험",
  anomaly:          "이상 신호",
  gini:             "쏠림 지수",
  rework:           "재작업",
  rejection_rate:   "반려율",
  bottleneck:       "정체 구간",
} as const;

export const FORECAST_LABELS: Record<string, string> = {
  p50: "보통",
  p85: "보수적",
  p95: "안전",
};

export const RISK_LABEL = (score: number): { label: string; color: string } => {
  if (score >= 70) return { label: "높음", color: "var(--color-critical)" };
  if (score >= 40) return { label: "주의", color: "var(--color-warning)" };
  return { label: "정상", color: "var(--color-normal)" };
};

export const STAGE_COLOR: Record<string, string> = {
  backlog:     "var(--color-stage-backlog)",
  in_progress: "var(--color-stage-in-progress)",
  review:      "var(--color-stage-review)",
  done:        "var(--color-stage-done)",
  blocked:     "var(--color-stage-blocked)",
};
