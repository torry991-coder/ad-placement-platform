import { useEffect, useState } from "react";
import {
  Activity, Eye, MousePointerClick, TrendingUp,
  DollarSign, AlertTriangle, Target, Zap,
} from "lucide-react";
import StatCard from "../components/common/StatCard";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { DashboardSkeleton } from "../components/common/Skeleton";
import { TrendChart } from "../components/dashboard/TrendChart";
import { PlatformPie } from "../components/dashboard/PlatformPie";
import { TopCampaignsBar } from "../components/dashboard/TopCampaignsBar";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

// ── Types ──────────────────────────────────────────────────

interface DashboardData {
  active_campaigns: number;
  total_impressions: number;
  total_clicks: number;
  total_conversions: number;
  total_spend: number;
  total_revenue: number;
  avg_ctr: number;
  avg_cvr: number;
  avg_cpc: number;
  avg_cpa: number;
  avg_roas: number;
  budget_utilization: number;
  platform_breakdown: PlatformBreakdown[];
  daily_trend: TrendPoint[];
}

interface PlatformBreakdown {
  platform: string;
  impressions: number;
  clicks: number;
  conversions: number;
  spend: number;
  revenue: number;
  ctr: number;
  cvr: number;
  roas: number;
}

interface TrendPoint {
  date: string;
  impressions: number;
  clicks: number;
  conversions: number;
  spend: number;
  revenue: number;
  ctr: number;
  cvr: number;
  cpc: number;
  roas: number;
}

interface CampaignSummary {
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

// ── Helpers ────────────────────────────────────────────────

const fmtNum = (n: number) => n?.toLocaleString("zh-CN") ?? "0";
const fmtMoney = (n: number) => `¥${Math.round(n).toLocaleString("zh-CN")}`;
const fmtPct = (n: number) => `${n?.toFixed(2)}%` ?? "0%";

// ── Component ──────────────────────────────────────────────

export default function DashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get("/api/analytics/dashboard");
      setData(res.data);
    } catch {
      setError("无法加载仪表盘数据");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchDashboard, 30000);
    return () => clearInterval(interval);
  }, []);

  // ── Loading ────────────────────────────────────────────

  if (loading) return <DashboardSkeleton />;

  // ── Error ──────────────────────────────────────────────

  if (error || !data) {
    return <ErrorState message={error ?? "数据加载失败"} onRetry={fetchDashboard} />;
  }

  // ── Derived ────────────────────────────────────────────

  const isEmpty = data.total_impressions === 0 && data.total_clicks === 0;

  if (isEmpty) {
    return (
      <EmptyState
        icon={Activity}
        title="暂无投放数据"
        description="系统尚未产生任何广告投放数据。创建广告活动并开始投放后，这里将展示实时数据。"
        action={{ label: "创建广告活动", onClick: () => (window.location.href = "/campaigns") }}
      />
    );
  }

  // Build campaign summaries from platform breakdown
  const campaignSummaries: CampaignSummary[] = (data.platform_breakdown || []).map(
    (p, i) => ({
      campaign_id: i + 1,
      campaign_name: PLATFORM_LABELS[p.platform] || p.platform,
      impressions: p.impressions,
      clicks: p.clicks,
      conversions: p.conversions,
      spend: p.spend,
      revenue: p.revenue,
      ctr: p.ctr,
      cvr: p.cvr,
      roas: p.roas,
    }),
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">广告投放总览</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            实时监控广告投放效果，数据每30秒自动刷新
          </p>
        </div>
        <button
          onClick={fetchDashboard}
          className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 flex items-center gap-1.5 transition-colors"
        >
          <Zap size={14} />
          刷新
        </button>
      </div>

      {/* KPI Cards Row 1 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-stagger">
        <StatCard
          title="活跃活动"
          value={data.active_campaigns}
          icon={Activity}
          trend="+2"
          trendUp
          compareLabel="较上周"
          iconColor="text-blue-500"
        />
        <StatCard
          title="展示量"
          value={fmtNum(data.total_impressions)}
          icon={Eye}
          trend="+12.5%"
          trendUp
          compareLabel="较昨日"
          iconColor="text-indigo-500"
        />
        <StatCard
          title="点击量"
          value={fmtNum(data.total_clicks)}
          icon={MousePointerClick}
          trend="+8.3%"
          trendUp
          compareLabel="较昨日"
          iconColor="text-cyan-500"
        />
        <StatCard
          title="转化量"
          value={fmtNum(data.total_conversions)}
          icon={TrendingUp}
          trend="+5.1%"
          trendUp
          compareLabel="较昨日"
          iconColor="text-emerald-500"
        />
      </div>

      {/* KPI Cards Row 2 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-stagger">
        <StatCard
          title="总花费"
          value={fmtMoney(data.total_spend)}
          icon={DollarSign}
          trend=""
          iconColor="text-rose-500"
        />
        <StatCard
          title="总收入"
          value={fmtMoney(data.total_revenue)}
          icon={DollarSign}
          trend={`ROAS ${data.avg_roas?.toFixed(1)}x`}
          trendUp={data.avg_roas >= 1.5}
          iconColor="text-emerald-500"
        />
        <StatCard
          title="平均CTR"
          value={fmtPct(data.avg_ctr)}
          icon={Target}
          trend={data.avg_ctr > 3.5 ? "优秀" : "需优化"}
          trendUp={data.avg_ctr > 3.5}
          iconColor="text-amber-500"
        />
        <StatCard
          title="预算利用率"
          value={`${data.budget_utilization?.toFixed(1)}%`}
          icon={AlertTriangle}
          trend={data.budget_utilization > 90 ? "接近上限" : "正常"}
          trendUp={data.budget_utilization <= 90}
          iconColor="text-violet-500"
        />
      </div>

      {/* Charts Row 1: Trend + Platform Pie */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <TrendChart data={data.daily_trend} />
        </div>
        <div>
          <PlatformPie data={data.platform_breakdown} />
        </div>
      </div>

      {/* Charts Row 2: Top Campaigns */}
      <TopCampaignsBar data={campaignSummaries} metric="roas" />

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "新建活动", path: "/campaigns", color: "bg-brand-600 hover:bg-brand-700" },
          { label: "A/B 实验", path: "/experiments", color: "bg-indigo-600 hover:bg-indigo-700" },
          { label: "AI 助手", path: "/ai-agent", color: "bg-emerald-600 hover:bg-emerald-700" },
          { label: "数据报告", path: "/reports", color: "bg-amber-600 hover:bg-amber-700" },
        ].map((btn) => (
          <button
            key={btn.label}
            onClick={() => navigate(btn.path)}
            className={`${btn.color} text-white text-sm font-medium py-2.5 px-4 rounded-lg transition-colors active:scale-95`}
          >
            {btn.label}
          </button>
        ))}
      </div>
    </div>
  );
}

const PLATFORM_LABELS: Record<string, string> = {
  simulated: "模拟平台",
  google: "Google Ads",
  meta: "Meta Ads",
  tiktok: "TikTok",
};
