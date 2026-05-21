"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchConnectors, testConnection, updateConnector, syncConnector,
  type ConnectorInstance,
} from "@/lib/api";
import { SectionCard } from "@/components/SectionCard";
import { Spinner } from "@/components/Spinner";
import { CheckCircle, XCircle, RefreshCw, Save, ExternalLink, AlertTriangle } from "lucide-react";
import { formatDateTime } from "@/lib/format";

interface FormState {
  instance_name: string;
  base_url: string;
  api_key: string;
  lookback_days: string;
}

export default function SettingsPage() {
  const [instance, setInstance] = useState<ConnectorInstance | null>(null);
  const [hasApiKey, setHasApiKey] = useState(false);
  const [form, setForm] = useState<FormState>({
    instance_name: "",
    base_url: "",
    api_key: "",
    lookback_days: "3650",
  });
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [syncResult, setSyncResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [saveMsg, setSaveMsg] = useState<{ ok: boolean; msg: string } | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setFetchError(null);
    fetchConnectors()
      .then((data) => {
        const inst = data.instances[0] ?? null;
        setInstance(inst);
        if (inst) {
          // api_key 존재 여부는 config에 키가 있는지로 판단 (마스킹되어 값은 없음)
          const cfgKeys = Object.keys(inst.config);
          setHasApiKey(cfgKeys.includes("api_key") || false);
          setForm({
            instance_name: inst.instance_name,
            base_url:      String(inst.config.base_url ?? ""),
            api_key:       "",
            lookback_days: String(inst.config.lookback_days ?? 3650),
          });
        }
      })
      .catch((e: Error) => setFetchError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleChange = (field: keyof FormState) =>
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [field]: e.target.value }));
    };

  const handleTest = async () => {
    if (!instance) return;
    if (!form.api_key && !hasApiKey) {
      setTestResult({ ok: false, msg: "API 키를 먼저 입력하고 저장하세요." });
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const config: Record<string, unknown> = { base_url: form.base_url };
      if (form.api_key) config.api_key = form.api_key;
      const res = await testConnection(instance.connector_type, config);
      setTestResult(res.ok
        ? { ok: true,  msg: `연결 성공 (${res.user ?? "확인됨"})` }
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
        base_url:      form.base_url,
        lookback_days: Number(form.lookback_days),
      };
      if (form.api_key) config.api_key = form.api_key;
      await updateConnector(instance.id, { instance_name: form.instance_name, config });
      setSaveMsg({ ok: true, msg: "저장 완료" });
      if (form.api_key) setHasApiKey(true);
      setForm((prev) => ({ ...prev, api_key: "" }));   // 저장 후 필드 초기화
    } catch (e) {
      setSaveMsg({ ok: false, msg: `저장 실패: ${(e as Error).message}` });
    } finally {
      setSaving(false);
    }
  };

  const handleSync = async () => {
    if (!instance) return;
    if (!hasApiKey && !form.api_key) {
      setSyncResult({ ok: false, msg: "API 키를 먼저 저장한 후 동기화하세요." });
      return;
    }
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await syncConnector(instance.id);
      const s = res.sync as Record<string, number>;
      setSyncResult({
        ok: true,
        msg: `동기화 완료 — 프로젝트 ${s.projects ?? 0}건, 이슈 ${s.issues ?? 0}건, 구성원 ${s.users ?? 0}명`,
      });
    } catch (e) {
      setSyncResult({ ok: false, msg: `동기화 실패: ${(e as Error).message}` });
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 p-6">
        <Spinner size={32} />
        <p className="text-sm" style={{ color: "var(--muted)" }}>설정 불러오는 중…</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h1 className="text-lg font-bold" style={{ color: "var(--foreground)" }}>연동 설정</h1>

      {/* API 연결 오류 */}
      {fetchError && (
        <div
          className="flex items-start gap-3 px-4 py-3 rounded-xl text-sm"
          style={{ backgroundColor: "var(--color-critical)12", border: "1px solid var(--color-critical)30", color: "var(--color-critical)" }}
        >
          <AlertTriangle size={16} className="shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium">백엔드 연결 실패</p>
            <p className="text-xs mt-0.5 opacity-80">{fetchError}</p>
            <p className="text-xs mt-1 opacity-70">
              백엔드가 실행 중인지 확인하세요: <code>uvicorn app.api.main:app --reload --port 8000</code>
            </p>
          </div>
          <button
            onClick={load}
            className="shrink-0 text-xs underline hover:no-underline"
          >
            재시도
          </button>
        </div>
      )}

      {instance ? (
        <SectionCard
          title="Redmine 연동"
          badge={
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{ backgroundColor: "var(--color-good)20", color: "var(--color-good)" }}
            >
              ✅ 활성
            </span>
          }
        >
          <div className="space-y-4">
            {instance.updated_at && (
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                마지막 업데이트: {formatDateTime(instance.updated_at)}
              </p>
            )}

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
                label={`API 키${hasApiKey ? " (저장됨 — 변경 시 입력)" : " *필수"}`}
                value={form.api_key}
                onChange={handleChange("api_key")}
                type="password"
                placeholder={hasApiKey ? "변경할 경우에만 입력" : "Redmine API 키를 입력하세요"}
                hint={
                  form.base_url ? (
                    <a
                      href={`${form.base_url}/my/api_key`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 hover:opacity-70"
                      style={{ color: "var(--color-accent)" }}
                    >
                      발급 방법 보기 <ExternalLink size={11} />
                    </a>
                  ) : null
                }
              />
              <FormField
                label="초기 수집 기간 (일)"
                value={form.lookback_days}
                onChange={handleChange("lookback_days")}
                type="number"
              />
            </div>

            {/* 결과 메시지들 */}
            {testResult && <ResultBanner ok={testResult.ok} msg={testResult.msg} />}
            {saveMsg   && <ResultBanner ok={saveMsg.ok}   msg={saveMsg.msg} />}
            {syncResult && (
              <ResultBanner ok={syncResult.ok} msg={syncResult.msg} />
            )}

            {/* 버튼 */}
            <div className="flex flex-wrap gap-2 pt-1">
              <ActionButton onClick={handleTest} loading={testing} icon={<CheckCircle size={14} />}>
                연결 테스트
              </ActionButton>
              <ActionButton onClick={handleSave} loading={saving} icon={<Save size={14} />}>
                저장
              </ActionButton>
              <ActionButton onClick={handleSync} loading={syncing} icon={<RefreshCw size={14} />} variant="primary">
                {syncing ? "동기화 중…" : "지금 동기화"}
              </ActionButton>
            </div>

            {syncing && (
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                최초 동기화는 수 분이 걸릴 수 있습니다 (~16,000건 예상). 페이지를 닫지 마세요.
              </p>
            )}
          </div>
        </SectionCard>
      ) : !fetchError ? (
        <div
          className="text-center py-10 rounded-2xl"
          style={{ border: "1px dashed var(--border)" }}
        >
          <p className="text-sm" style={{ color: "var(--muted)" }}>연동 설정이 없습니다.</p>
        </div>
      ) : null}

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

function ResultBanner({ ok, msg }: { ok: boolean; msg: string }) {
  return (
    <div
      className="flex items-center gap-2 text-sm px-3 py-2 rounded-lg"
      style={{
        backgroundColor: ok ? "var(--color-good)15" : "var(--color-critical)15",
        color: ok ? "var(--color-good)" : "var(--color-critical)",
      }}
    >
      {ok ? <CheckCircle size={15} /> : <XCircle size={15} />}
      {msg}
    </div>
  );
}

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
        className="w-full px-3 py-2 rounded-lg text-sm outline-none"
        style={{
          backgroundColor: "var(--background)",
          border: "1px solid var(--border)",
          color: "var(--foreground)",
        }}
      />
      {hint && <div className="text-xs mt-0.5">{hint}</div>}
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
      className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium hover:opacity-80 disabled:opacity-50 transition-opacity"
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
