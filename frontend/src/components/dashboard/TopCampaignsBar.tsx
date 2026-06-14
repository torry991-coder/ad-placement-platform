import { useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { BarChart3 } from "lucide-react";

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

interface Props {
  data: CampaignSummary[];
  loading?: boolean;
  metric?: "roas" | "ctr" | "cvr" | "spend";
  limit?: number;
}

const METRIC_CONFIG: Record<string, { label: string; color: string; format: (v: number) => string }> = {
  roas: { label: "ROAS", color: "#f59e0b", format: (v) => `${v.toFixed(2)}x` },
  ctr: { label: "CTR %", color: "#3b82f6", format: (v) => `${v.toFixed(2)}%` },
  cvr: { label: "CVR %", color: "#10b981", format: (v) => `${v.toFixed(2)}%` },
  spend: { label: "花费 ¥", color: "#ef4444", format: (v) => `¥${v.toLocaleString()}` },
};

export function TopCampaignsBar({ data, loading, metric = "roas", limit = 5 }: Props) {
  const config = METRIC_CONFIG[metric];

  const chartData = useMemo(() => {
    return [...data]
      .sort((a, b) => (b[metric] as number) - (a[metric] as number))
      .slice(0, limit)
      .map((c) => ({
        name: c.campaign_name.length > 10
          ? c.campaign_name.slice(0, 10) + "..."
          : c.campaign_name,
        fullName: c.campaign_name,
        value: Number((c[metric] as number).toFixed(2)),
      }))
      .reverse(); // horizontal bar: top at top
  }, [data, metric, limit]);

  if (loading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-36 bg-gray-200 dark:bg-gray-700 rounded mb-4" />
        <div className="h-[260px] bg-gray-100 dark:bg-gray-800 rounded" />
      </div>
    );
  }

  if (!chartData.length) {
    return (
      <div className="card p-5 flex flex-col items-center justify-center h-[300px] text-gray-400">
        <BarChart3 size={40} className="mb-2 opacity-30" />
        <p className="text-sm">暂无活动数据</p>
      </div>
    );
  }

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          Top {limit} 活动 - {config.label}
        </h3>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ left: 10, right: 20 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            horizontal={false}
            stroke="currentColor"
            className="text-gray-200 dark:text-gray-700"
          />
          <XAxis
            type="number"
            tick={{ fontSize: 11 }}
            stroke="currentColor"
            className="text-gray-400 dark:text-gray-500"
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 12 }}
            stroke="currentColor"
            className="text-gray-400 dark:text-gray-500"
            width={100}
          />
          <Tooltip
            formatter={(value: number) => [config.format(value), config.label]}
            labelFormatter={(label, payload) => {
              const item = payload?.[0] as any;
              return item?.payload?.fullName ?? label;
            }}
            contentStyle={{
              background: "var(--tw-card-bg, #1f2937)",
              border: "1px solid var(--tw-card-border, #374151)",
              borderRadius: "8px",
              fontSize: "13px",
            }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={24}>
            {chartData.map((_, idx) => (
              <Cell key={idx} fill={config.color} opacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
