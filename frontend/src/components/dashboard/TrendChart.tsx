import { useMemo } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { TrendingUp } from "lucide-react";

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

interface Props {
  data: TrendPoint[];
  loading?: boolean;
}

const METRICS = [
  { key: "ctr", label: "CTR %", color: "#3b82f6", stroke: "#3b82f6" },
  { key: "cvr", label: "CVR %", color: "#10b981", stroke: "#10b981" },
  { key: "roas", label: "ROAS", color: "#f59e0b", stroke: "#f59e0b" },
] as const;

export function TrendChart({ data, loading }: Props) {
  const chartData = useMemo(() => {
    return data.map((d) => ({
      date: d.date?.slice(5) ?? d.date, // MM-DD
      ctr: Number(d.ctr?.toFixed(2)),
      cvr: Number(d.cvr?.toFixed(2)),
      roas: Number(d.roas?.toFixed(2)),
    }));
  }, [data]);

  if (loading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-40 bg-gray-200 dark:bg-gray-700 rounded mb-4" />
        <div className="h-[300px] bg-gray-100 dark:bg-gray-800 rounded" />
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="card p-5 flex flex-col items-center justify-center h-[340px] text-gray-400">
        <TrendingUp size={40} className="mb-2 opacity-30" />
        <p className="text-sm">暂无趋势数据</p>
      </div>
    );
  }

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          7日关键指标趋势
        </h3>
        <div className="flex gap-3 text-xs text-gray-400">
          {METRICS.map((m) => (
            <span key={m.key} className="flex items-center gap-1">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: m.color }}
              />
              {m.label}
            </span>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="currentColor"
            className="text-gray-200 dark:text-gray-700"
          />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            stroke="currentColor"
            className="text-gray-400 dark:text-gray-500"
          />
          <YAxis
            tick={{ fontSize: 12 }}
            stroke="currentColor"
            className="text-gray-400 dark:text-gray-500"
          />
          <Tooltip
            contentStyle={{
              background: "var(--tw-card-bg, #1f2937)",
              border: "1px solid var(--tw-card-border, #374151)",
              borderRadius: "8px",
              fontSize: "13px",
            }}
          />
          <Legend />
          {METRICS.map((m) => (
            <Line
              key={m.key}
              type="monotone"
              dataKey={m.key}
              stroke={m.stroke}
              name={m.label}
              dot={false}
              strokeWidth={2}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
