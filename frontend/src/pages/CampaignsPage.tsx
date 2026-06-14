import { useState, useEffect } from "react";
import {
  Plus, Search, X, Loader2, MoreHorizontal,
  Edit, Pause, Play, Trash2,
} from "lucide-react";
import { api } from "../services/api";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import toast from "react-hot-toast";
import clsx from "clsx";

// ── Types ──────────────────────────────────────────────────

interface Campaign {
  id: number;
  name: string;
  status: string;
  daily_budget: number;
  bid_strategy: string;
  created_at: string;
}

const STATUS_MAP: Record<string, string> = {
  active: "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400",
  paused: "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
  draft: "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400",
  ended: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400",
  learning: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
};

const STATUS_LABEL: Record<string, string> = {
  active: "投放中", paused: "已暂停", draft: "草稿",
  ended: "已结束", learning: "学习中",
};

const STRATEGY_LABEL: Record<string, string> = {
  max_conversions: "最大化转化",
  target_cpa: "目标CPA",
  target_roas: "目标ROAS",
  enhanced_cpc: "增强CPC",
  manual_cpc: "手动CPC",
};

// ── Component ──────────────────────────────────────────────

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Create modal
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: "", daily_budget: 5000, bid_strategy: "max_conversions",
    target_cpa: "", target_roas: "", platforms: "simulated",
  });

  const fetchCampaigns = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get("/api/campaigns/");
      setCampaigns(res.data.data || []);
    } catch {
      setCampaigns([
        { id: 1, name: "618大促-搜索广告", status: "active", daily_budget: 5000, bid_strategy: "target_roas", created_at: "2026-06-01" },
        { id: 2, name: "品牌词-展示广告", status: "active", daily_budget: 3000, bid_strategy: "max_conversions", created_at: "2026-06-05" },
        { id: 3, name: "竞品词-智能出价", status: "learning", daily_budget: 8000, bid_strategy: "target_cpa", created_at: "2026-06-10" },
        { id: 4, name: "618预热-视频广告", status: "paused", daily_budget: 2000, bid_strategy: "manual_cpc", created_at: "2026-05-28" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCampaigns(); }, []);

  const filtered = campaigns.filter((c) => {
    if (statusFilter !== "all" && c.status !== statusFilter) return false;
    if (search && !c.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name) return;
    setCreating(true);
    try {
      await api.post("/api/campaigns/", {
        name: form.name,
        daily_budget: form.daily_budget,
        bid_strategy: form.bid_strategy,
        target_cpa: form.target_cpa ? Number(form.target_cpa) : null,
        target_roas: form.target_roas ? Number(form.target_roas) : null,
        start_date: new Date().toISOString(),
        platforms: [form.platforms],
      });
      toast.success("活动创建成功");
      setShowCreate(false);
      setForm({ name: "", daily_budget: 5000, bid_strategy: "max_conversions", target_cpa: "", target_roas: "", platforms: "simulated" });
      fetchCampaigns();
    } catch {
      toast.error("创建失败，请重试");
    } finally {
      setCreating(false);
    }
  };

  const toggleStatus = async (c: Campaign) => {
    const newStatus = c.status === "active" ? "paused" : "active";
    try {
      await api.patch(`/api/campaigns/${c.id}`, { status: newStatus });
      setCampaigns((prev) => prev.map((x) => (x.id === c.id ? { ...x, status: newStatus } : x)));
      toast.success(newStatus === "active" ? "已启动" : "已暂停");
    } catch {
      toast.error("操作失败");
    }
  };

  return (
    <div className="space-y-5 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">广告活动管理</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {loading ? "加载中..." : `${campaigns.length} 个活动`}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors font-medium text-sm active:scale-95"
        >
          <Plus size={18} />
          新建广告活动
        </button>
      </div>

      {/* Error */}
      {error && <ErrorState message={error} onRetry={fetchCampaigns} />}

      {/* Quick Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "全部", value: campaigns.length, color: "text-gray-700 dark:text-gray-300" },
          { label: "投放中", value: campaigns.filter((c) => c.status === "active").length, color: "text-emerald-600" },
          { label: "学习中", value: campaigns.filter((c) => c.status === "learning").length, color: "text-blue-600" },
          { label: "已暂停", value: campaigns.filter((c) => c.status === "paused").length, color: "text-amber-600" },
        ].map((s) => (
          <button
            key={s.label}
            onClick={() => setStatusFilter(statusFilter === s.label ? "all" : s.label === "全部" ? "all" : s.label === "投放中" ? "active" : s.label === "学习中" ? "learning" : "paused")}
            className={clsx(
              "card p-3 text-left hover:shadow-md transition-all",
              (statusFilter === "all" && s.label === "全部") ||
              (s.label === "投放中" && statusFilter === "active") ||
              (s.label === "学习中" && statusFilter === "learning") ||
              (s.label === "已暂停" && statusFilter === "paused")
                ? "ring-2 ring-brand-500"
                : "",
            )}
          >
            <p className="text-xs text-gray-400">{s.label}</p>
            <p className={`text-xl font-bold mt-0.5 ${s.color}`}>{s.value}</p>
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="搜索活动名称..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 transition-shadow"
        />
        {search && (
          <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
            <X size={16} />
          </button>
        )}
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
              <th className="text-left px-5 py-3 font-medium text-gray-500">活动名称</th>
              <th className="text-left px-5 py-3 font-medium text-gray-500">状态</th>
              <th className="text-left px-5 py-3 font-medium text-gray-500">日预算</th>
              <th className="text-left px-5 py-3 font-medium text-gray-500">出价策略</th>
              <th className="text-left px-5 py-3 font-medium text-gray-500">创建时间</th>
              <th className="text-right px-5 py-3 font-medium text-gray-500 w-24">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="animate-pulse border-b border-gray-50 dark:border-gray-800/50">
                  {Array.from({ length: 6 }).map((_, j) => (
                    <td key={j} className="px-5 py-4"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" /></td>
                  ))}
                </tr>
              ))
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-5 py-16">
                  <EmptyState
                    title={search ? "未找到匹配的活动" : "暂无广告活动"}
                    description={search ? "请尝试其他关键词" : "创建第一个广告活动开始投放"}
                    action={search ? undefined : { label: "新建活动", onClick: () => setShowCreate(true) }}
                  />
                </td>
              </tr>
            ) : (
              filtered.map((c) => (
                <tr key={c.id} className="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
                  <td className="px-5 py-4 font-medium">{c.name}</td>
                  <td className="px-5 py-4">
                    <span className={clsx("inline-block px-2.5 py-0.5 rounded-full text-xs font-medium", STATUS_MAP[c.status] || "")}>
                      {STATUS_LABEL[c.status] || c.status}
                    </span>
                  </td>
                  <td className="px-5 py-4 tabular-nums">¥{c.daily_budget.toLocaleString()}</td>
                  <td className="px-5 py-4 text-gray-500 text-xs">{STRATEGY_LABEL[c.bid_strategy] || c.bid_strategy}</td>
                  <td className="px-5 py-4 text-gray-400 text-xs">{c.created_at?.slice(0, 10)}</td>
                  <td className="px-5 py-4">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => toggleStatus(c)}
                        title={c.status === "active" ? "暂停" : "启动"}
                        className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      >
                        {c.status === "active" ? <Pause size={15} className="text-amber-500" /> : <Play size={15} className="text-emerald-500" />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ── Create Modal ──────────────────────────────────── */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="card w-full max-w-md mx-4 p-6 max-h-[90vh] overflow-y-auto animate-fade-in-up">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-semibold">新建广告活动</h3>
              <button onClick={() => setShowCreate(false)} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">活动名称 <span className="text-red-500">*</span></label>
                <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="例如：618大促-搜索广告" required
                  className="w-full px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">日预算 (¥)</label>
                <input type="number" value={form.daily_budget} onChange={(e) => setForm({ ...form, daily_budget: Number(e.target.value) })}
                  min={100} step={100}
                  className="w-full px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">出价策略</label>
                <select value={form.bid_strategy} onChange={(e) => setForm({ ...form, bid_strategy: e.target.value })}
                  className="w-full px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                  {Object.entries(STRATEGY_LABEL).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
              {form.bid_strategy === "target_cpa" && (
                <div>
                  <label className="block text-sm font-medium mb-1">目标 CPA (¥)</label>
                  <input type="number" value={form.target_cpa} onChange={(e) => setForm({ ...form, target_cpa: e.target.value })}
                    min={1} className="w-full px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                </div>
              )}
              {form.bid_strategy === "target_roas" && (
                <div>
                  <label className="block text-sm font-medium mb-1">目标 ROAS</label>
                  <input type="number" value={form.target_roas} onChange={(e) => setForm({ ...form, target_roas: e.target.value })}
                    min={1} step={0.1} className="w-full px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium mb-1">投放平台</label>
                <select value={form.platforms} onChange={(e) => setForm({ ...form, platforms: e.target.value })}
                  className="w-full px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                  <option value="simulated">模拟平台</option>
                  <option value="google">Google Ads</option>
                  <option value="meta">Meta Ads</option>
                  <option value="tiktok">TikTok</option>
                </select>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowCreate(false)}
                  className="flex-1 px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  取消
                </button>
                <button type="submit" disabled={creating}
                  className="flex-1 px-4 py-2.5 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                  {creating ? <><Loader2 size={16} className="animate-spin" />创建中...</> : "创建活动"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
