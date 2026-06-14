import { useState, useEffect } from "react";
import { FlaskConical, Play, Square, BarChart3, Plus, X } from "lucide-react";
import { api } from "../services/api";
import clsx from "clsx";

// ── Types ────────────────────────────────────────────────────────────────────

interface Experiment {
  id: number;
  name: string;
  status: "draft" | "running" | "stopped" | "completed";
  control_campaign_id: number;
  variant_campaign_id: number;
  traffic_split: number;
  hypothesis: string;
  created_at: string;
  started_at: string | null;
  stopped_at: string | null;
}

interface ExperimentResults {
  p_value: number;
  confidence_level: number;
  is_significant: boolean;
  winner_variant: string | null;
  control_metrics: Record<string, number>;
  variant_metrics: Record<string, number>;
  bayesian_prob: number;
}

interface CreateExperimentPayload {
  name: string;
  control_campaign_id: number;
  variant_campaign_id: number;
  traffic_split: number;
  hypothesis: string;
}

// ── Constants ────────────────────────────────────────────────────────────────

const STATUS_MAP: Record<string, string> = {
  draft: "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400",
  running:
    "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400",
  stopped:
    "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
  completed:
    "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
};

const STATUS_LABEL: Record<string, string> = {
  draft: "草稿",
  running: "运行中",
  stopped: "已停止",
  completed: "已完成",
};

const METRIC_LABELS: Record<string, string> = {
  impressions: "展示量",
  clicks: "点击量",
  conversions: "转化量",
  spend: "花费",
  revenue: "收入",
  ctr: "CTR",
  cvr: "CVR",
  cpc: "CPC",
  cpa: "CPA",
  roas: "ROAS",
};

// ── Initial form state ───────────────────────────────────────────────────────

const emptyForm: CreateExperimentPayload = {
  name: "",
  control_campaign_id: 0,
  variant_campaign_id: 0,
  traffic_split: 50,
  hypothesis: "",
};

// ── Component ────────────────────────────────────────────────────────────────

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create modal
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<CreateExperimentPayload>({ ...emptyForm });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  // Results modal
  const [showResults, setShowResults] = useState(false);
  const [results, setResults] = useState<ExperimentResults | null>(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState("");

  // Action loading states
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  // ── Fetch experiments ────────────────────────────────────────────────────

  const fetchExperiments = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get("/api/experiments/");
      const list = res.data?.data || res.data || [];
      setExperiments(Array.isArray(list) ? list : []);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "加载实验列表失败";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExperiments();
  }, []);

  // ── Create experiment ────────────────────────────────────────────────────

  const handleCreate = async () => {
    if (!form.name.trim()) {
      setCreateError("请输入实验名称");
      return;
    }
    setCreating(true);
    setCreateError("");
    try {
      await api.post("/api/experiments/", form);
      setShowCreate(false);
      setForm({ ...emptyForm });
      fetchExperiments();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "创建实验失败";
      setCreateError(msg);
    } finally {
      setCreating(false);
    }
  };

  // ── Start / Stop ─────────────────────────────────────────────────────────

  const handleAction = async (id: number, action: "start" | "stop") => {
    setActionLoading(id);
    try {
      await api.post(`/api/experiments/${id}/${action}`);
      fetchExperiments();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || `操作失败`;
      setError(msg);
    } finally {
      setActionLoading(null);
    }
  };

  // ── View results ─────────────────────────────────────────────────────────

  const handleViewResults = async (id: number) => {
    setShowResults(true);
    setResults(null);
    setResultsLoading(true);
    setResultsError("");
    try {
      const res = await api.get(`/api/experiments/${id}/results`);
      setResults(res.data?.data || res.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "加载实验结果失败";
      setResultsError(msg);
    } finally {
      setResultsLoading(false);
    }
  };

  // ── Format helpers ───────────────────────────────────────────────────────

  const fmtPct = (v: number) => `${(v * 100).toFixed(2)}%`;
  const fmtNum = (v: number) => v?.toLocaleString("zh-CN") ?? "-";

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">A/B 实验管理</h2>
          <p className="text-sm text-gray-500 mt-1">
            创建和管理广告投放对比实验，优化投放策略
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors font-medium text-sm"
        >
          <Plus size={18} />
          新建实验
        </button>
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
                实验名称
              </th>
              <th className="text-left px-6 py-3 font-medium text-gray-500">
                状态
              </th>
              <th className="text-left px-6 py-3 font-medium text-gray-500">
                流量分配
              </th>
              <th className="text-left px-6 py-3 font-medium text-gray-500">
                假设
              </th>
              <th className="text-left px-6 py-3 font-medium text-gray-500">
                创建时间
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
            ) : experiments.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-16 text-center text-gray-400">
                  <FlaskConical size={32} className="mx-auto mb-2 opacity-30" />
                  暂无实验数据，点击"新建实验"开始
                </td>
              </tr>
            ) : (
              experiments.map((exp) => (
                <tr
                  key={exp.id}
                  className="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors"
                >
                  <td className="px-6 py-4 font-medium flex items-center gap-2">
                    <FlaskConical size={16} className="text-brand-500" />
                    {exp.name}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={clsx(
                        "inline-block px-2.5 py-0.5 rounded-full text-xs font-medium",
                        STATUS_MAP[exp.status]
                      )}
                    >
                      {STATUS_LABEL[exp.status] || exp.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-500">
                    对照 {100 - exp.traffic_split}% / 实验 {exp.traffic_split}%
                  </td>
                  <td className="px-6 py-4 text-gray-500 max-w-[200px] truncate">
                    {exp.hypothesis || "-"}
                  </td>
                  <td className="px-6 py-4 text-gray-400">{exp.created_at}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-1.5">
                      {exp.status === "draft" || exp.status === "stopped" ? (
                        <button
                          onClick={() => handleAction(exp.id, "start")}
                          disabled={actionLoading === exp.id}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30 rounded-lg hover:bg-emerald-100 dark:hover:bg-emerald-900/50 disabled:opacity-50"
                        >
                          <Play size={13} />
                          {actionLoading === exp.id ? "执行中..." : "启动"}
                        </button>
                      ) : null}
                      {exp.status === "running" ? (
                        <button
                          onClick={() => handleAction(exp.id, "stop")}
                          disabled={actionLoading === exp.id}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-900/50 disabled:opacity-50"
                        >
                          <Square size={13} />
                          {actionLoading === exp.id ? "执行中..." : "停止"}
                        </button>
                      ) : null}
                      <button
                        onClick={() => handleViewResults(exp.id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50"
                      >
                        <BarChart3 size={13} />
                        查看结果
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ── Create Modal ──────────────────────────────────────────────────── */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="card w-full max-w-lg mx-4 p-6 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-semibold">新建 A/B 实验</h3>
              <button
                onClick={() => {
                  setShowCreate(false);
                  setCreateError("");
                }}
                className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  实验名称
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) =>
                    setForm({ ...form, name: e.target.value })
                  }
                  placeholder="例如：新出价策略对比测试"
                  className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    对照活动 ID
                  </label>
                  <input
                    type="number"
                    value={form.control_campaign_id || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        control_campaign_id: Number(e.target.value),
                      })
                    }
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    实验活动 ID
                  </label>
                  <input
                    type="number"
                    value={form.variant_campaign_id || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        variant_campaign_id: Number(e.target.value),
                      })
                    }
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  实验组流量分配 ({form.traffic_split}%)
                </label>
                <input
                  type="range"
                  min={1}
                  max={99}
                  value={form.traffic_split}
                  onChange={(e) =>
                    setForm({ ...form, traffic_split: Number(e.target.value) })
                  }
                  className="w-full accent-brand-600"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>对照 {100 - form.traffic_split}%</span>
                  <span>实验 {form.traffic_split}%</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  实验假设
                </label>
                <textarea
                  value={form.hypothesis}
                  onChange={(e) =>
                    setForm({ ...form, hypothesis: e.target.value })
                  }
                  placeholder="例如：使用目标ROAS出价策略后，ROAS将提升20%"
                  rows={3}
                  className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                />
              </div>

              {createError && (
                <p className="text-sm text-red-500">{createError}</p>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => {
                    setShowCreate(false);
                    setCreateError("");
                  }}
                  className="px-4 py-2.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  取消
                </button>
                <button
                  onClick={handleCreate}
                  disabled={creating}
                  className="px-4 py-2.5 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors font-medium disabled:opacity-50"
                >
                  {creating ? "创建中..." : "创建实验"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Results Modal ─────────────────────────────────────────────────── */}
      {showResults && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="card w-full max-w-2xl mx-4 p-6 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <BarChart3 size={20} className="text-brand-500" />
                实验结果
              </h3>
              <button
                onClick={() => {
                  setShowResults(false);
                  setResults(null);
                  setResultsError("");
                }}
                className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <X size={20} />
              </button>
            </div>

            {resultsLoading ? (
              <div className="py-16 text-center text-gray-400">
                <div className="w-6 h-6 mx-auto mb-3 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                加载结果中...
              </div>
            ) : resultsError ? (
              <div className="py-8 text-center text-red-500 text-sm">
                {resultsError}
              </div>
            ) : results ? (
              <div className="space-y-5">
                {/* Summary */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50">
                    <p className="text-xs text-gray-500 mb-1">P 值</p>
                    <p className="text-xl font-bold">{results.p_value.toFixed(4)}</p>
                  </div>
                  <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50">
                    <p className="text-xs text-gray-500 mb-1">置信水平</p>
                    <p className="text-xl font-bold">
                      {fmtPct(results.confidence_level)}
                    </p>
                  </div>
                  <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50">
                    <p className="text-xs text-gray-500 mb-1">
                      统计显著性
                    </p>
                    <span
                      className={clsx(
                        "inline-block px-2.5 py-0.5 rounded-full text-xs font-medium mt-1",
                        results.is_significant
                          ? "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400"
                          : "bg-gray-100 dark:bg-gray-800 text-gray-500"
                      )}
                    >
                      {results.is_significant ? "显著" : "不显著"}
                    </span>
                  </div>
                  <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50">
                    <p className="text-xs text-gray-500 mb-1">
                      贝叶斯概率
                    </p>
                    <p className="text-xl font-bold">
                      {fmtPct(results.bayesian_prob)}
                    </p>
                  </div>
                </div>

                {/* Winner */}
                {results.winner_variant && (
                  <div className="p-4 rounded-lg bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800">
                    <p className="text-sm font-medium text-brand-700 dark:text-brand-400">
                      优胜变体：{results.winner_variant}
                    </p>
                  </div>
                )}

                {/* Metrics comparison */}
                <div>
                  <h4 className="text-sm font-semibold mb-3">指标对比</h4>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 dark:border-gray-800">
                        <th className="text-left py-2 font-medium text-gray-500">
                          指标
                        </th>
                        <th className="text-right py-2 font-medium text-gray-500">
                          对照组
                        </th>
                        <th className="text-right py-2 font-medium text-gray-500">
                          实验组
                        </th>
                        <th className="text-right py-2 font-medium text-gray-500">
                          变化
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.keys(results.control_metrics).map((key) => {
                        const control = results.control_metrics[key];
                        const variant = results.variant_metrics[key];
                        const diff =
                          control !== 0
                            ? ((variant - control) / Math.abs(control)) * 100
                            : 0;
                        return (
                          <tr
                            key={key}
                            className="border-b border-gray-50 dark:border-gray-800/50"
                          >
                            <td className="py-2.5">
                              {METRIC_LABELS[key] || key}
                            </td>
                            <td className="text-right py-2.5 tabular-nums">
                              {fmtNum(control)}
                            </td>
                            <td className="text-right py-2.5 tabular-nums">
                              {fmtNum(variant)}
                            </td>
                            <td
                              className={clsx(
                                "text-right py-2.5 tabular-nums font-medium",
                                diff > 0
                                  ? "text-emerald-600"
                                  : diff < 0
                                  ? "text-red-500"
                                  : "text-gray-400"
                              )}
                            >
                              {diff > 0 ? "+" : ""}
                              {diff.toFixed(1)}%
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={() => setShowResults(false)}
                    className="px-4 py-2.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    关闭
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
