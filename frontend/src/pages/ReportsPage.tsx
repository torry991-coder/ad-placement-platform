import { useState, useEffect, useMemo } from "react";
import {
  FileText,
  Download,
  TrendingUp,
  Eye,
  MousePointerClick,
  DollarSign,
  CreditCard,
  Loader2,
  ChevronDown,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api } from "../services/api";
import DataTable from "../components/common/DataTable";
import StatCard from "../components/common/StatCard";
import { ColumnDef } from "@tanstack/react-table";

interface ReportSummary {
  impressions: number;
  clicks: number;
  conversions: number;
  spend: number;
  revenue: number;
  ctr: number;
  cvr: number;
  roas: number;
}

interface CampaignBreakdown {
  campaign_id: number;
  campaign_name: string;
  impressions: number;
  clicks: number;
  conversions: number;
  spend: number;
  revenue: number;
  ctr: number;
  cvr: number;
  roas: number;
}

interface DailyTrend {
  date: string;
  impressions: number;
  clicks: number;
  conversions: number;
}

interface ReportData {
  summary: ReportSummary;
  campaign_breakdown: CampaignBreakdown[];
  daily_trend: DailyTrend[];
}

interface CampaignOption {
  id: number;
  name: string;
}

const METRIC_OPTIONS = [
  { key: "impressions", label: "展示量" },
  { key: "clicks", label: "点击量" },
  { key: "conversions", label: "转化量" },
  { key: "spend", label: "花费" },
  { key: "revenue", label: "收入" },
  { key: "ctr", label: "CTR" },
  { key: "cvr", label: "CVR" },
  { key: "roas", label: "ROAS" },
];

export default function ReportsPage() {
  const [reportType, setReportType] = useState<"daily" | "hourly">("daily");
  const [campaignId, setCampaignId] = useState<string>("all");
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString().slice(0, 10);
  });
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().slice(0, 10));
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([
    "impressions", "clicks", "conversions", "spend", "revenue",
  ]);
  const [generating, setGenerating] = useState(false);
  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [campaigns, setCampaigns] = useState<CampaignOption[]>([]);
  const [exporting, setExporting] = useState<string | null>(null);

  useEffect(() => {
    api
      .get("/api/campaigns/")
      .then((res) => {
        const data = res.data.data || res.data || [];
        setCampaigns(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        setCampaigns([
          { id: 1, name: "618大促-搜索广告" },
          { id: 2, name: "品牌词-展示广告" },
          { id: 3, name: "竞品词-智能出价" },
        ]);
      });
  }, []);

  const toggleMetric = (key: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const generateReport = async () => {
    setGenerating(true);
    try {
      const res = await api.post("/api/reports/generate", {
        report_type: reportType,
        campaign_id: campaignId === "all" ? null : Number(campaignId),
        date_from: dateFrom,
        date_to: dateTo,
        metrics: selectedMetrics,
      });
      setReportData(res.data.data || res.data);
    } catch {
      // Demo data
      const mockSummary: ReportSummary = {
        impressions: 2457800,
        clicks: 98312,
        conversions: 4521,
        spend: 125680.5,
        revenue: 389450.75,
        ctr: 4.0,
        cvr: 4.6,
        roas: 3.1,
      };
      const mockBreakdown: CampaignBreakdown[] = [
        { campaign_id: 1, campaign_name: "618大促-搜索广告", impressions: 890000, clicks: 42000, conversions: 2100, spend: 52000, revenue: 182000, ctr: 4.72, cvr: 5.0, roas: 3.5 },
        { campaign_id: 2, campaign_name: "品牌词-展示广告", impressions: 1200000, clicks: 38000, conversions: 1600, spend: 38000, revenue: 114000, ctr: 3.17, cvr: 4.21, roas: 3.0 },
        { campaign_id: 3, campaign_name: "竞品词-智能出价", impressions: 367800, clicks: 18312, conversions: 821, spend: 35680.5, revenue: 93450.75, ctr: 4.98, cvr: 4.48, roas: 2.62 },
      ];
      const mockTrend: DailyTrend[] = Array.from({ length: 7 }, (_, i) => {
        const d = new Date(dateFrom);
        d.setDate(d.getDate() + i);
        return {
          date: d.toISOString().slice(0, 10),
          impressions: Math.floor(250000 + Math.random() * 150000),
          clicks: Math.floor(8000 + Math.random() * 8000),
          conversions: Math.floor(400 + Math.random() * 400),
        };
      });
      setReportData({ summary: mockSummary, campaign_breakdown: mockBreakdown, daily_trend: mockTrend });
    } finally {
      setGenerating(false);
    }
  };

  const handleExport = async (format: "csv" | "pdf" | "xlsx") => {
    setExporting(format);
    try {
      const params = new URLSearchParams({
        report_type: reportType,
        campaign_id: campaignId === "all" ? "" : campaignId,
        date_from: dateFrom,
        date_to: dateTo,
      });
      const res = await api.get(`/api/reports/export/${format}?${params.toString()}`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${Date.now()}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Demo: create a simple blob for download
      const text =
        format === "csv"
          ? "日期,展示量,点击量,转化量,花费,收入\n2026-06-08,350000,12000,550,18000,54000\n2026-06-09,380000,14000,620,19500,58500\n"
          : "REPORT PDF PLACEHOLDER";
      const blob = new Blob([text], { type: format === "csv" ? "text/csv" : "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${Date.now()}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(null);
    }
  };

  const breakdownColumns = useMemo<ColumnDef<CampaignBreakdown>[]>(
    () => [
      {
        accessorKey: "campaign_name",
        header: "广告活动",
        cell: ({ getValue }) => <span className="font-medium">{getValue<string>()}</span>,
      },
      {
        accessorKey: "impressions",
        header: "展示量",
        cell: ({ getValue }) => <span className="tabular-nums">{getValue<number>().toLocaleString()}</span>,
      },
      {
        accessorKey: "clicks",
        header: "点击量",
        cell: ({ getValue }) => <span className="tabular-nums">{getValue<number>().toLocaleString()}</span>,
      },
      {
        accessorKey: "conversions",
        header: "转化量",
        cell: ({ getValue }) => <span className="tabular-nums">{getValue<number>().toLocaleString()}</span>,
      },
      {
        accessorKey: "spend",
        header: "花费",
        cell: ({ getValue }) => <span className="tabular-nums">¥{getValue<number>().toLocaleString()}</span>,
      },
      {
        accessorKey: "revenue",
        header: "收入",
        cell: ({ getValue }) => <span className="tabular-nums">¥{getValue<number>().toLocaleString()}</span>,
      },
      {
        accessorKey: "ctr",
        header: "CTR",
        cell: ({ getValue }) => <span className="tabular-nums">{getValue<number>().toFixed(2)}%</span>,
      },
      {
        accessorKey: "cvr",
        header: "CVR",
        cell: ({ getValue }) => <span className="tabular-nums">{getValue<number>().toFixed(2)}%</span>,
      },
      {
        accessorKey: "roas",
        header: "ROAS",
        cell: ({ getValue }) => {
          const v = getValue<number>();
          return (
            <span className={`tabular-nums font-medium ${v >= 3 ? "stat-up" : "stat-down"}`}>
              {v.toFixed(1)}x
            </span>
          );
        },
      },
    ],
    []
  );

  const fmt = (n: number) => n.toLocaleString("zh-CN");
  const fmtMoney = (n: number) => `¥${fmt(Math.round(n))}`;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">数据报表</h2>
          <p className="text-sm text-gray-500 mt-1">
            生成和分析广告投放报表，支持导出CSV/PDF
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport("xlsx")}
            disabled={exporting === "xlsx" || !reportData}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {exporting === "xlsx" ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
            导出Excel
          </button>
          <button
            onClick={() => handleExport("csv")}
            disabled={exporting === "csv" || !reportData}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {exporting === "csv" ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
            导出CSV
          </button>
          <button
            onClick={() => handleExport("pdf")}
            disabled={exporting === "pdf" || !reportData}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {exporting === "pdf" ? <Loader2 size={16} className="animate-spin" /> : <FileText size={16} />}
            导出PDF
          </button>
        </div>
      </div>

      {/* Report config */}
      <div className="card p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Report type */}
          <div>
            <label className="block text-sm font-medium mb-1.5 text-gray-500">报表类型</label>
            <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
              <button
                onClick={() => setReportType("daily")}
                className={`flex-1 px-3 py-2 text-sm font-medium transition-colors ${
                  reportType === "daily"
                    ? "bg-brand-600 text-white"
                    : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
                }`}
              >
                日报
              </button>
              <button
                onClick={() => setReportType("hourly")}
                className={`flex-1 px-3 py-2 text-sm font-medium transition-colors ${
                  reportType === "hourly"
                    ? "bg-brand-600 text-white"
                    : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
                }`}
              >
                小时报
              </button>
            </div>
          </div>

          {/* Campaign */}
          <div>
            <label className="block text-sm font-medium mb-1.5 text-gray-500">广告活动</label>
            <div className="relative">
              <select
                value={campaignId}
                onChange={(e) => setCampaignId(e.target.value)}
                className="w-full appearance-none px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 pr-8"
              >
                <option value="all">全部活动</option>
                {campaigns.map((c) => (
                  <option key={c.id} value={String(c.id)}>
                    {c.name}
                  </option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {/* Date From */}
          <div>
            <label className="block text-sm font-medium mb-1.5 text-gray-500">开始日期</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {/* Date To */}
          <div>
            <label className="block text-sm font-medium mb-1.5 text-gray-500">结束日期</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {/* Generate button */}
          <div className="flex items-end">
            <button
              onClick={generateReport}
              disabled={generating}
              className="w-full px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {generating ? <Loader2 size={16} className="animate-spin" /> : <TrendingUp size={16} />}
              {generating ? "生成中..." : "生成报表"}
            </button>
          </div>
        </div>

        {/* Metrics multi-select */}
        <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
          <label className="block text-sm font-medium mb-2 text-gray-500">选择指标</label>
          <div className="flex flex-wrap gap-2">
            {METRIC_OPTIONS.map((metric) => (
              <button
                key={metric.key}
                onClick={() => toggleMetric(metric.key)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  selectedMetrics.includes(metric.key)
                    ? "bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400 border border-brand-300 dark:border-brand-700"
                    : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:bg-gray-200 dark:hover:bg-gray-700"
                }`}
              >
                {metric.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Generated report */}
      {reportData && (
        <>
          {/* Summary cards */}
          <div>
            <h3 className="text-lg font-semibold mb-3">数据概览</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              <StatCard title="展示量" value={fmt(reportData.summary.impressions)} icon={Eye} trend="" />
              <StatCard title="点击量" value={fmt(reportData.summary.clicks)} icon={MousePointerClick} trend="" />
              <StatCard title="转化量" value={fmt(reportData.summary.conversions)} icon={TrendingUp} trend="" />
              <StatCard title="花费" value={fmtMoney(reportData.summary.spend)} icon={DollarSign} trend="" />
              <StatCard title="收入" value={fmtMoney(reportData.summary.revenue)} icon={CreditCard} trend="" />
              <StatCard title="CTR" value={`${reportData.summary.ctr.toFixed(2)}%`} icon={MousePointerClick} trend="" />
              <StatCard title="CVR" value={`${reportData.summary.cvr.toFixed(2)}%`} icon={TrendingUp} trend="" />
              <StatCard
                title="ROAS"
                value={`${reportData.summary.roas.toFixed(1)}x`}
                icon={TrendingUp}
                trend=""
              />
            </div>
          </div>

          {/* Trend chart */}
          <div className="card p-5">
            <h3 className="text-lg font-semibold mb-4">每日展示量趋势</h3>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={reportData.daily_trend}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(val) => val.slice(5)}
                  className="text-gray-500 text-xs"
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickFormatter={(val) => (val >= 10000 ? `${(val / 10000).toFixed(0)}万` : val)}
                  className="text-gray-500 text-xs"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "white",
                    borderRadius: "8px",
                    border: "1px solid #e5e7eb",
                    fontSize: "12px",
                  }}
                  formatter={(value: number) => [value.toLocaleString(), "展示量"]}
                  labelFormatter={(label) => `日期: ${label}`}
                />
                <Line
                  type="monotone"
                  dataKey="impressions"
                  stroke="#4f46e5"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Campaign breakdown table */}
          <div>
            <h3 className="text-lg font-semibold mb-3">广告活动明细</h3>
            <DataTable
              columns={breakdownColumns}
              data={reportData.campaign_breakdown}
              searchable={false}
              emptyText="暂无活动数据"
            />
          </div>
        </>
      )}

      {/* Empty state */}
      {!reportData && !generating && (
        <div className="card p-16 text-center">
          <FileText size={48} className="mx-auto text-gray-300 dark:text-gray-600 mb-4" />
          <p className="text-gray-500 text-lg mb-2">选择条件并生成报表</p>
          <p className="text-sm text-gray-400">设置报表类型、日期范围和指标后，点击"生成报表"查看数据</p>
        </div>
      )}
    </div>
  );
}
