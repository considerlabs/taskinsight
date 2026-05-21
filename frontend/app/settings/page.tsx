"use client";

import { useEffect, useState } from "react";
import {
  fetchConnectors, testConnection, updateConnector, syncConnector,
  type ConnectorInstance,
} from "@/lib/api";
import { SectionCard } from "@/components/SectionCard";
import { Spinner } from "@/components/Spinner";
import { CheckCircle, XCircle, RefreshCw, Save, ExternalLink } from "lucide-react";
import { formatDateTime } from "@/lib/format";

interface FormState {
  instance_name: string;
  base_url: string;
  api_key: string;
  lookback_days: number;
}

export default function SettingsPage() {
  const [instance, setInstance] = useState<ConnectorInstance | null>(null);
  const [form, setForm] = useState<FormState>({
    instance_name: "",
    base_url: "",
    api_key: "",
    lookback_days: 3650,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchConnectors()
      .then((data) => {
        const inst = data.instances[0] ?? null;
        setInstance(inst);
        if (inst) {
          setForm({
            instance_name: inst.instance_name,
            base_url:      String(inst.config.base_url ?? ""),
            api_key:       "",  // 마스킹되어 반환되므로 빈 값으로
            lookback_days: Number(inst.config.lookback_days ?? 3650),
          });
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const handleChange = (field: keyof FormState) =>
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleTest = async () => {
    if (!instance) return;
    setTesting(true);
    setTestResult(null);
    try {
      const config = { base_url: form.base_url, api_key: form.api_key || undefined };
      const res = await testConnection(instance.connector_type, config);
      setTestResult(res.ok
        ? { ok: true,  msg: `연결 성공 (${res.user ?? ""})` }
        : { ok: false, msg: res.error ?? "연결 실패" }
      );
    } catch (e) {
      setTestResult({ ok: false, msg: (e as Error).message });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (!instance) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      const config: Record<string, unknown> = {
        base_url: form.base_url,
        lookback_days: form.lookback_days,
      };
      if (form.api_key) config.api_key = form.api_key;
      await updateConnector(instance.id, { instance_name: form.instance_name, config });
      setSaveMsg("저장 완료");
    } catch (e) {
      setSaveMsg(`저장 실패: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleSync = async () => {
    if (!instance) return;
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await syncConnector(instance.id);
      const s = res.sync as Record<string, number>;
      setSyncResult(`동기화 완료 — 프로젝트 ${s.projects ?? 0}건, 이슈 ${s.issues ?? 0}건, 구성원 ${s.users ?? 0}명`);
    } catch (e) {
      setSyncResult(`동기화 실패: ${(e as Error).message}`);
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-16 p-6">
        <Spinner size={32} />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h1 className="text-lg font-bold" style={{ color: "var(--foreground)" }}>연동 설정</h1>

      {instance ? (
        <SectionCard
          title={instance.instance_name}
          badge={
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{
                backgroundColor: "var(--color-good)20",
                color: "var(--color-good)",
              }}
            >
              ✅ 활성
            </span>
          }
        >
          <div className="space-y-4">
            {/* 마지막 동기화 */}
            {instance.updated_at && (
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                마지막 업데이트: {formatDateTime(instance.updated_at)}
              </p>
            )}

            {/* 폼 */}
            <div className="space-y-3">
              <FormField
                label="연동 이름"
                value={form.instance_name}
                onChange={handleChange("instance_name")}
              />
              <FormField
                label="Redmine URL"
                value={form.base_url}
                onChange={handleChange("base_url")}
                placeholder="http://redmine.example.com:5555/redmine"
              />
              <FormField
                label="API 키"
                value={form.api_key}
                onChange={handleChange("api_key")}
                type="password"
                placeholder="••••••••••••• (변경 시에만 입력)"
                hint={
                  <a
                    href={form.base_url ? `${form.base_url}/my/api_key` : "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 hover:opacity-70"
                    style={{ color: "var(--color-accent)" }}
                  >
                    발급 방법 보기 <ExternalLink size={11} />
                  </a>
                }
              />
              <FormField
                label="초기 수집 기간 (일)"
                value={String(form.lookback_days)}
                onChange={handleChange("lookback_days")}
                type="number"
              />
            </div>

            {/* 테스트 결과 */}
            {testResult && (
              <div
                className="flex items-center gap-2 text-sm px-3 py-2 rounded-lg"
                style={{
                  backgroundColor: testResult.ok ? "var(--color-good)15" : "var(--color-critical)15",
                  color: testResult.ok ? "var(--color-good)" : "var(--color-critical)",
                }}
              >
                {testResult.ok ? <CheckCircle size={15} /> : <XCircle size={15} />}
                {testResult.msg}
              </div>
            )}

            {saveMsg && (
              <p className="text-sm" style={{ color: saveMsg.includes("실패") ? "var(--color-critical)" : "var(--color-good)" }}>
                {saveMsg}
              </p>
            )}

            {syncResult && (
              <div
                className="text-sm px-3 py-2 rounded-lg"
                style={{
                  backgroundColor: syncResult.includes("실패") ? "var(--color-critical)15" : "var(--color-good)15",
                  color: syncResult.includes("실패") ? "var(--color-critical)" : "var(--color-good)",
                }}
              >
                {syncResult}
              </div>
            )}

            {/* 버튼 그룹 */}
            <div className="flex gap-2 pt-1">
              <ActionButton onClick={handleTest} loading={testing} icon={<CheckCircle size={14} />} variant="ghost">
                연결 테스트
              </ActionButton>
              <ActionButton onClick={handleSave} loading={saving} icon={<Save size={14} />} variant="ghost">
                저장
              </ActionButton>
              <ActionButton onClick={handleSync} loading={syncing} icon={<RefreshCw size={14} />} variant="primary">
                {syncing ? "동기화 중…" : "지금 동기화"}
              </ActionButton>
            </div>
          </div>
        </SectionCard>
      ) : (
        <div
          className="text-center py-10 rounded-2xl"
          style={{ border: "1px dashed var(--border)" }}
        >
          <p className="text-sm" style={{ color: "var(--muted)" }}>연동 설정이 없습니다.</p>
        </div>
      )}

      {/* Coming soon */}
      <div
        className="rounded-2xl px-5 py-4"
        style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
      >
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          다른 업무관리 도구 연동은 추후 지원 예정입니다.
          <br />
          <span className="text-xs">(Jira, Asana, ClickUp, Notion 등)</span>
        </p>
      </div>
    </div>
  );
}

// ─── 내부 컴포넌트 ────────────────────────────────────────────────────────────

interface FormFieldProps {
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  type?: string;
  placeholder?: string;
  hint?: React.ReactNode;
}

function FormField({ label, value, onChange, type = "text", placeholder, hint }: FormFieldProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium" style={{ color: "var(--muted)" }}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full px-3 py-2 rounded-lg text-sm outline-none transition-colors"
        style={{
          backgroundColor: "var(--background)",
          border: "1px solid var(--border)",
          color: "var(--foreground)",
        }}
      />
      {hint && <div className="text-xs">{hint}</div>}
    </div>
  );
}

interface ActionButtonProps {
  onClick: () => void;
  loading: boolean;
  icon: React.ReactNode;
  variant?: "ghost" | "primary";
  children: React.ReactNode;
}

function ActionButton({ onClick, loading, icon, variant = "ghost", children }: ActionButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-opacity hover:opacity-80 disabled:opacity-50"
      style={
        variant === "primary"
          ? { backgroundColor: "var(--color-accent)", color: "#fff" }
          : { backgroundColor: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }
      }
    >
      {loading ? <Spinner size={14} /> : icon}
      {children}
    </button>
  );
}
