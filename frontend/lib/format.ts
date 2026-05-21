/** 날짜/숫자 포맷 유틸 */

export function formatDays(days: number): string {
  if (days >= 365) return `${(days / 365).toFixed(1)}년`;
  if (days >= 30)  return `${Math.round(days / 30)}개월`;
  return `${Math.round(days)}일`;
}

export function formatCount(n: number): string {
  return n.toLocaleString("ko-KR") + "건";
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleDateString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit" });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString("ko-KR", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

/** 위험점수 → 이모지 */
export function riskEmoji(score: number): string {
  if (score >= 70) return "🔴";
  if (score >= 40) return "🟠";
  return "⚪";
}

/** 전주 대비 변화 → 화살표 문자열 */
export function deltaMark(delta: number): string {
  if (delta > 0) return `↑${delta}`;
  if (delta < 0) return `↓${Math.abs(delta)}`;
  return "변화 없음";
}
