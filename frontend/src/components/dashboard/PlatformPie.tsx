import { useMemo } from "react";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { PieChartIcon } from "lucide-react";

interface PlatformData {
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

interface Props {
  data: PlatformData[];
  loading?: boolean;
}

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];
const PLATFORM_LABELS: Record<string, string> = {
  simulated: "模拟平台",
  google: "Google Ads",
  meta: "Meta Ads",
  tiktok: "TikTok",
};

export function PlatformPie({ data, loading }: Props) {
  const chartData = useMemo(() => {
    return data
      .filter((d) => d.spend > 0)
      .map((d) => ({
        name: PLATFORM_LABELS[d.platform] || d.platform,
        value: Math.round(d.spend * 100) / 100,
        roas: d.roas,
      }));
  }, [data]);

  if (loading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded mb-4" />
        <div className="h-[260px] bg-gray-100 dark:bg-gray-800 rounded" />
      </div>
    );
  }

  if (!chartData.length) {
    return (
      <div className="card p-5 flex flex-col items-center justify-center h-[300px] text-gray-400">
        <PieChartIcon size={40} className="mb-2 opacity-30" />
        <p className="text-sm">暂无平台分布数据</p>
      </div>
    );
  }

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
        平台花费分布
      </h3>
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={90}
            paddingAngle={3}
            dataKey="value"
          >
            {chartData.map((_, idx) => (
              <Cell
                key={idx}
                fill={COLORS[idx % COLORS.length]}
                stroke="transparent"
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number) => `¥${value.toLocaleString()}`}
            contentStyle={{
              background: "var(--tw-card-bg, #1f2937)",
              border: "1px solid var(--tw-card-border, #374151)",
              borderRadius: "8px",
              fontSize: "13px",
            }}
          />
          <Legend
            formatter={(value: string) => (
              <span className="text-xs text-gray-600 dark:text-gray-400">
                {value}
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
