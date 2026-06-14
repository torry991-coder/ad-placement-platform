import { useState, useEffect } from "react";
import {
  Bell,
  AlertTriangle,
  ShieldAlert,
  Zap,
  Plus,
  X,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import { api } from "../services/api";
import clsx from "clsx";

// ── Types ────────────────────────────────────────────────────────────────────

interface AlertRule {
  id: number;
  name: string;
  metric: string;
  operator: string;
  threshold: number;
  severity: "info" | "warning" | "critical";
  action: string;
  enabled: boolean;
  created_at: string;
}

interface TriggeredAlert {
  rule_id: number;
  rule_name: string;
  severity: string;
  metric: string;
  current_value: number;
  threshold: number;
  message: string;
  triggered_at: string;
}

interface CreateAlertPayload {
  name: string;
  metric: string;
  operator: string;
  threshold: number;
  severity: string;
  action: string;
}

// ── Constants ────────────────────────────────────────────────────────────────

const METRIC_OPTIONS = [
  { value: "ctr", label: "CTR (点击率)" },
  { value: "cvr", label: "CVR (转化率)" },
  { value: "cpc", label: "CPC (每次点击成本)" },
  { value: "cpa", label: "CPA (每次转化成本)" },
  { value: "roas", label: "ROAS (广告支出回报)" },
  { value: "spend", label: "花费" },
];

const OPERATOR_OPTIONS = [
  { value: ">", label: "大于 >" },
  { value: ">=", label: "大于等于 ≥" },
  { value: "<", label: "小于 <" },
  { value: "<=", label: "小于等于 ≤" },
];

const SEVERITY_OPTIONS = [
  { value: "info", label: "信息" },
  { value: "warning", label: "警告" },
  { value: "critical", label: "严重" },
];

const ACTION_OPTIONS = [
  { value: "notify", label: "发送通知" },
  { value: "pause_campaign", label: "暂停活动" },
  { value: "adjust_budget", label: "调整预算" },
  { value: "escalate", label: "升级处理" },
];

const SEVERITY_BADGE: Record<string, string> = {
  info: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
  warning:
    "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
  critical: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400",
};

const SEVERITY_LABEL: Record<string, string> = {
  info: "信息",
  warning: "警告",
  critical: "严重",
};

const OPERATOR_SYMBOLS: Record<string, string> = {
  ">": ">",
  ">=": "≥",
  "<": "<",
  "<=": "≤",
};

const METRIC_LABEL_MAP: Record<string, string> = {
  ctr: "CTR",
  cvr: "CVR",
  cpc: "CPC",
  cpa: "CPA",
  roas: "ROAS",
  spend: "花费",
};

// ── Empty form ───────────────────────────────────────────────────────────────

const emptyForm: CreateAlertPayload = {
  name: "",
  metric: "ctr",
  operator: "<",
  threshold: 0,
  severity: "warning",
  action: "notify",
};

// ── Component ────────────────────────────────────────────────────────────────

export default function AlertsPage() {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create / Edit modal
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<CreateAlertPayload>({ ...emptyForm });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  // Evaluate
  const [evaluating, setEvaluating] = useState(false);
  const [triggeredAlerts, setTriggeredAlerts] = useState<TriggeredAlert[]>([]);
  const [showEvaluate, setShowEvaluate] = useState(false);

  // ── Fetch rules ──────────────────────────────────────────────────────────

  const fetchRules = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get("/api/alerts/");
      const list = res.data?.data || res.data || [];
      setRules(Array.isArray(list) ? list : []);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "加载告警规则失败";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  // ── Toggle enable ────────────────────────────────────────────────────────

  const handleToggle = async (rule: AlertRule) => {
    try {
      await api.patch(`/api/alerts/${rule.id}`, { enabled: !rule.enabled });
      setRules((prev) =>
        prev.map((r) =>
          r.id === rule.id ? { ...r, enabled: !r.enabled } : r
        )
      );
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "更新失败";
      setError(msg);
    }
  };

  // ── Save (create / update) ───────────────────────────────────────────────

  const handleSave = async () => {
    if (!form.name.trim()) {
      setFormError("请输入规则名称");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      if (editId !== null) {
        await api.patch(`/api/alerts/${editId}`, form);
      } else {
        await api.post("/api/alerts/", form);
      }
      setShowForm(false);
      setEditId(null);
      setForm({ ...emptyForm });
      fetchRules();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "保存失败";
      setFormError(msg);
    } finally {
      setSaving(false);
    }
  };

  // ── Delete ───────────────────────────────────────────────────────────────

  const handleDelete = async (id: number) => {
    if (!window.confirm("确定要删除这条告警规则吗？")) return;
    try {
      await api.delete(`/api/alerts/${id}`);
      fetchRules();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "删除失败";
      setError(msg);
    }
  };

  // ── Evaluate ─────────────────────────────────────────────────────────────

  const handleEvaluate = async () => {
    setEvaluating(true);
    setTriggeredAlerts([]);
    try {
      const res = await api.post("/api/alerts/evaluate");
      const alerts = res.data?.data || res.data || [];
      setTriggeredAlerts(Array.isArray(alerts) ? alerts : []);
      setShowEvaluate(true);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "评估失败";
      setError(msg);
    } finally {
      setEvaluating(false);
    }
  };

  // ── Open edit ────────────────────────────────────────────────────────────

  const openEdit = (rule: AlertRule) => {
    setEditId(rule.id);
    setForm({
      name: rule.name,
      metric: rule.metric,
      operator: rule.operator,
      threshold: rule.threshold,
      severity: rule.severity,
      action: rule.action,
    });
    setShowForm(true);
  };

  const openCreate = () => {
    setEditId(null);
    setForm({ ...emptyForm });
    setShowForm(true);
  };

  // ── Helpers ──────────────────────────────────────────────────────────────

  const renderCondition = (rule: AlertRule) =>
    `${METRIC_LABEL_MAP[rule.metric] || rule.metric} ${
      OPERATOR_SYMBOLS[rule.operator] || rule.operator
    } ${rule.threshold}`;

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">告警中心</h2>
          <p className="text-sm text-gray-500 mt-1">
            管理告警规则，监控关键指标异常并及时响应
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleEvaluate}
            disabled={evaluating}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 text-sm font-medium disabled:opacity-50"
          >
            <Zap size={16} className="text-amber-500" />
            {evaluating ? "评估中..." : "立即评估"}
          </button>
          <button
            onClick={openCreate}
            className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors font-medium text-sm"
          >
            <Plus size={18} />
            新建规则
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-3 underline hover:no-underline"
          >
            关闭
          </button>
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
              <th className="text-left px-6 py-3 font-medium text-gray-500">
                规则名称
              </th>
              <th className="text-left px-6 py-3 font-medium text-gray-500">
                严重级别
              </th>
              <th className="text-left px-6 py-3 font-medium text-gray-500">
                触发条件
              </th>
              <th className="text-left px-6 py-3 font-medium text-gray-500">
                执行动作
              </th>
              <th className="text-center px-6 py-3 font-medium text-gray-500">
                状态
              </th>
              <th className="text-right px-6 py-3 font-medium text-gray-500">
                操作
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-6 py-16 text-center text-gray-400">
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                    加载中...
                  </div>
                </td>
              </tr>
            ) : rules.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-16 text-center text-gray-400">
                  <Bell size={32} className="mx-auto mb-2 opacity-30" />
                  暂无告警规则，点击"新建规则"开始配置
                </td>
              </tr>
            ) : (
              rules.map((rule) => (
                <tr
                  key={rule.id}
                  className={clsx(
                    "border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors",
                    !rule.enabled && "opacity-50"
                  )}
                >
                  <td className="px-6 py-4 font-medium flex items-center gap-2">
                    {rule.severity === "critical" ? (
                      <ShieldAlert size={16} className="text-red-500" />
                    ) : rule.severity === "warning" ? (
                      <AlertTriangle size={16} className="text-amber-500" />
                    ) : (
                      <Bell size={16} className="text-blue-500" />
                    )}
                    {rule.name}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={clsx(
                        "inline-block px-2.5 py-0.5 rounded-full text-xs font-medium",
                        SEVERITY_BADGE[rule.severity]
                      )}
                    >
                      {SEVERITY_LABEL[rule.severity] || rule.severity}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-600 dark:text-gray-300 font-mono text-xs">
                    {renderCondition(rule)}
                  </td>
                  <td className="px-6 py-4 text-gray-500">
                    {ACTION_OPTIONS.find((a) => a.value === rule.action)
                      ?.label || rule.action}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <button
                      onClick={() => handleToggle(rule)}
                      className="inline-flex items-center"
                    >
                      {rule.enabled ? (
                        <ToggleRight
                          size={28}
                          className="text-emerald-500 hover:text-emerald-600"
                        />
                      ) : (
                        <ToggleLeft
                          size={28}
                          className="text-gray-300 dark:text-gray-600 hover:text-gray-400"
                        />
                      )}
                    </button>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => openEdit(rule)}
                        className="text-xs text-brand-600 dark:text-brand-400 hover:underline"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDelete(rule.id)}
                        className="text-xs text-red-500 hover:underline"
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ── Create / Edit Modal ───────────────────────────────────────────── */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="card w-full max-w-lg mx-4 p-6 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-semibold">
                {editId !== null ? "编辑告警规则" : "新建告警规则"}
              </h3>
              <button
                onClick={() => {
                  setShowForm(false);
                  setEditId(null);
                  setFormError("");
                }}
                className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  规则名称
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) =>
                    setForm({ ...form, name: e.target.value })
                  }
                  placeholder="例如：CTR过低告警"
                  className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    监控指标
                  </label>
                  <select
                    value={form.metric}
                    onChange={(e) =>
                      setForm({ ...form, metric: e.target.value })
                    }
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    {METRIC_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    操作符
                  </label>
                  <select
                    value={form.operator}
                    onChange={(e) =>
                      setForm({ ...form, operator: e.target.value })
                    }
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    {OPERATOR_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  阈值
                </label>
                <input
                  type="number"
                  step="any"
                  value={form.threshold}
                  onChange={(e) =>
                    setForm({ ...form, threshold: Number(e.target.value) })
                  }
                  className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    严重级别
                  </label>
                  <select
                    value={form.severity}
                    onChange={(e) =>
                      setForm({ ...form, severity: e.target.value })
                    }
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    {SEVERITY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    执行动作
                  </label>
                  <select
                    value={form.action}
                    onChange={(e) =>
                      setForm({ ...form, action: e.target.value })
                    }
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    {ACTION_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {formError && (
                <p className="text-sm text-red-500">{formError}</p>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => {
                    setShowForm(false);
                    setEditId(null);
                    setFormError("");
                  }}
                  className="px-4 py-2.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  取消
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-4 py-2.5 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors font-medium disabled:opacity-50"
                >
                  {saving ? "保存中..." : editId !== null ? "保存修改" : "创建规则"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Evaluate Results Modal ────────────────────────────────────────── */}
      {showEvaluate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="card w-full max-w-lg mx-4 p-6 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <AlertTriangle size={20} className="text-amber-500" />
                评估结果
              </h3>
              <button
                onClick={() => {
                  setShowEvaluate(false);
                  setTriggeredAlerts([]);
                }}
                className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <X size={20} />
              </button>
            </div>

            {triggeredAlerts.length === 0 ? (
              <div className="py-12 text-center text-gray-400">
                <Bell size={40} className="mx-auto mb-3 opacity-30" />
                当前没有触发任何告警规则，一切正常
              </div>
            ) : (
              <div className="space-y-3">
                {triggeredAlerts.map((alert, idx) => (
                  <div
                    key={idx}
                    className={clsx(
                      "p-4 rounded-lg border",
                      alert.severity === "critical"
                        ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
                        : alert.severity === "warning"
                        ? "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800"
                        : "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800"
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium text-sm">
                          {alert.rule_name}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {alert.message}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          当前值: {alert.current_value} / 阈值:{" "}
                          {alert.threshold} · 触发时间: {alert.triggered_at}
                        </p>
                      </div>
                      <span
                        className={clsx(
                          "inline-block px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0",
                          SEVERITY_BADGE[alert.severity]
                        )}
                      >
                        {SEVERITY_LABEL[alert.severity] || alert.severity}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end mt-5">
              <button
                onClick={() => {
                  setShowEvaluate(false);
                  setTriggeredAlerts([]);
                }}
                className="px-4 py-2.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
