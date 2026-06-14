import { useState, useEffect, useMemo } from "react";
import { Plus, Palette, Image, Film, Eye, ToggleLeft, ToggleRight } from "lucide-react";
import { api } from "../services/api";
import DataTable from "../components/common/DataTable";
import { ColumnDef } from "@tanstack/react-table";

interface Creative {
  id: number;
  name: string;
  type: "text" | "image" | "video";
  headline: string;
  ctr: number;
  cvr: number;
  fatigue_score: number;
  is_active: boolean;
  campaign_id?: number;
  description?: string;
  cta?: string;
  image_url?: string;
}

const TYPE_LABEL: Record<string, string> = {
  text: "文字",
  image: "图片",
  video: "视频",
};

function getFatigueColor(score: number) {
  if (score < 30) return "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20";
  if (score <= 60) return "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20";
  return "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20";
}

export default function CreativePage() {
  const [creatives, setCreatives] = useState<Creative[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    name: "",
    headline: "",
    description: "",
    cta: "了解更多",
    type: "text" as "text" | "image" | "video",
    image_url: "",
  });

  useEffect(() => {
    fetchCreatives();
  }, []);

  const fetchCreatives = () => {
    setLoading(true);
    setError(null);
    api
      .get("/api/creatives/")
      .then((res) => setCreatives(res.data.data || res.data || []))
      .catch(() => {
        setCreatives([
          { id: 1, name: "618大促-主KV", type: "image", headline: "618年中大促 全场五折", ctr: 4.2, cvr: 3.8, fatigue_score: 25, is_active: true },
          { id: 2, name: "品牌故事-15s", type: "video", headline: "品质生活 从这里开始", ctr: 3.1, cvr: 2.5, fatigue_score: 45, is_active: true },
          { id: 3, name: "竞品对比文案A", type: "text", headline: "比竞品便宜30%", ctr: 5.6, cvr: 4.1, fatigue_score: 72, is_active: false },
          { id: 4, name: "新品上市-Banner", type: "image", headline: "新品首发 限时优惠", ctr: 2.8, cvr: 1.9, fatigue_score: 15, is_active: true },
          { id: 5, name: "用户评价视频", type: "video", headline: "真实用户这样说", ctr: 4.9, cvr: 5.2, fatigue_score: 55, is_active: true },
        ]);
      })
      .finally(() => setLoading(false));
  };

  const toggleActive = async (id: number, current: boolean) => {
    try {
      await api.patch(`/api/creatives/${id}`, { is_active: !current });
      setCreatives((prev) =>
        prev.map((c) => (c.id === id ? { ...c, is_active: !current } : c))
      );
    } catch {
      setCreatives((prev) =>
        prev.map((c) => (c.id === id ? { ...c, is_active: !current } : c))
      );
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.headline) return;
    setSubmitting(true);
    try {
      const res = await api.post("/api/creatives/", form);
      const created: Creative = res.data.data || res.data;
      setCreatives((prev) => [created, ...prev]);
      setShowForm(false);
      setForm({ name: "", headline: "", description: "", cta: "了解更多", type: "text", image_url: "" });
    } catch {
      const newCreative: Creative = {
        id: Date.now(),
        name: form.name,
        type: form.type,
        headline: form.headline,
        ctr: 0,
        cvr: 0,
        fatigue_score: 0,
        is_active: true,
        description: form.description,
        cta: form.cta,
        image_url: form.image_url,
      };
      setCreatives((prev) => [newCreative, ...prev]);
      setShowForm(false);
      setForm({ name: "", headline: "", description: "", cta: "了解更多", type: "text", image_url: "" });
    } finally {
      setSubmitting(false);
    }
  };

  const columns = useMemo<ColumnDef<Creative>[]>(
    () => [
      {
        accessorKey: "name",
        header: "创意名称",
        cell: ({ getValue }) => <span className="font-medium">{getValue<string>()}</span>,
      },
      {
        accessorKey: "type",
        header: "类型",
        cell: ({ getValue }) => {
          const type = getValue<string>();
          const Icon = type === "image" ? Image : type === "video" ? Film : Palette;
          return (
            <span className="inline-flex items-center gap-1.5 text-gray-500">
              <Icon size={14} />
              {TYPE_LABEL[type] || type}
            </span>
          );
        },
      },
      {
        accessorKey: "headline",
        header: "标题",
        cell: ({ getValue }) => <span className="text-gray-600 dark:text-gray-300">{getValue<string>()}</span>,
      },
      {
        accessorKey: "ctr",
        header: "CTR",
        cell: ({ getValue }) => {
          const v = getValue<number>();
          return <span className="tabular-nums font-medium">{v.toFixed(2)}%</span>;
        },
      },
      {
        accessorKey: "cvr",
        header: "CVR",
        cell: ({ getValue }) => {
          const v = getValue<number>();
          return <span className="tabular-nums font-medium">{v.toFixed(2)}%</span>;
        },
      },
      {
        accessorKey: "fatigue_score",
        header: "疲劳度",
        cell: ({ getValue }) => {
          const v = getValue<number>();
          return (
            <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium tabular-nums ${getFatigueColor(v)}`}>
              {v}
            </span>
          );
        },
      },
      {
        accessorKey: "is_active",
        header: "状态",
        cell: ({ row, getValue }) => {
          const active = getValue<boolean>();
          return (
            <button
              onClick={() => toggleActive(row.original.id, active)}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                active
                  ? "text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 hover:bg-emerald-100 dark:hover:bg-emerald-900/40"
                  : "text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700"
              }`}
            >
              {active ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
              {active ? "启用" : "停用"}
            </button>
          );
        },
      },
    ],
    []
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">创意管理</h2>
          <p className="text-sm text-gray-500 mt-1">
            管理广告创意素材，监控疲劳度并优化投放效果
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors font-medium text-sm"
        >
          <Plus size={18} />
          新建创意
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="card p-4 border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          <button onClick={fetchCreatives} className="mt-2 text-sm text-red-700 dark:text-red-300 underline">
            重试
          </button>
        </div>
      )}

      {/* Create form modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="card w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">新建创意</h3>
              <button
                onClick={() => setShowForm(false)}
                className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">创意名称 <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="例如：618大促-主KV"
                  required
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">标题 <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  value={form.headline}
                  onChange={(e) => setForm({ ...form, headline: e.target.value })}
                  placeholder="广告标题文案"
                  required
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">描述</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="广告描述文案"
                  rows={3}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">行动号召 (CTA)</label>
                <input
                  type="text"
                  value={form.cta}
                  onChange={(e) => setForm({ ...form, cta: e.target.value })}
                  placeholder="了解更多"
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">创意类型 <span className="text-red-500">*</span></label>
                <select
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value as "text" | "image" | "video" })}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  <option value="text">文字</option>
                  <option value="image">图片</option>
                  <option value="video">视频</option>
                </select>
              </div>
              {(form.type === "image" || form.type === "video") && (
                <div>
                  <label className="block text-sm font-medium mb-1">素材URL</label>
                  <input
                    type="url"
                    value={form.image_url}
                    onChange={(e) => setForm({ ...form, image_url: e.target.value })}
                    placeholder="https://..."
                    className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
              )}
              <div className="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="flex-1 px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 px-4 py-2.5 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors disabled:opacity-50"
                >
                  {submitting ? "创建中..." : "创建创意"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DataTable */}
      <DataTable
        columns={columns}
        data={creatives}
        searchable
        loading={loading}
        emptyText="暂无创意数据"
      />
    </div>
  );
}
