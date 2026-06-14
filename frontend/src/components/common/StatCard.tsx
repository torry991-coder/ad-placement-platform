import { type LucideIcon, TrendingUp, TrendingDown, Minus } from "lucide-react";
import clsx from "clsx";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: string;
  trendUp?: boolean;
  compareLabel?: string;
  sparklineData?: number[];
  onClick?: () => void;
  className?: string;
  iconColor?: string;
}

function MiniSparkline({ data }: { data: number[] }) {
  const width = 60;
  const height = 24;
  if (data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");

  const isUp = data[data.length - 1] >= data[0];

  return (
    <svg width={width} height={height} className="opacity-60">
      <polyline
        points={points}
        fill="none"
        stroke={isUp ? "#10b981" : "#ef4444"}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  trendUp,
  compareLabel,
  sparklineData,
  onClick,
  className,
  iconColor,
}: StatCardProps) {
  const Wrapper = onClick ? "button" : "div";

  return (
    <Wrapper
      onClick={onClick}
      className={clsx(
        "card-hover p-5 text-left w-full transition-all duration-200",
        onClick && "cursor-pointer hover:shadow-md active:scale-[0.98]",
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1 min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
              {title}
            </p>
            {compareLabel && (
              <span className="text-[10px] text-gray-400 dark:text-gray-500 whitespace-nowrap">
                {compareLabel}
              </span>
            )}
          </div>

          <div className="flex items-baseline gap-2">
            <p className="text-2xl font-bold tracking-tight tabular-nums">
              {value}
            </p>
            {trend && trendUp !== undefined && (
              <span
                className={clsx(
                  "inline-flex items-center gap-0.5 text-xs font-semibold rounded-full px-1.5 py-0.5",
                  trendUp
                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                    : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
                )}
              >
                {trendUp ? (
                  <TrendingUp size={12} />
                ) : (
                  <TrendingDown size={12} />
                )}
                {trend}
              </span>
            )}
            {trend && trendUp === undefined && (
              <span className="inline-flex items-center gap-0.5 text-xs text-gray-400">
                <Minus size={12} />
                {trend}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {sparklineData && <MiniSparkline data={sparklineData} />}
          <div
            className={clsx(
              "p-2.5 rounded-xl",
              iconColor || "bg-gray-100 dark:bg-gray-800",
            )}
          >
            <Icon
              size={20}
              className={iconColor || "text-gray-500 dark:text-gray-400"}
            />
          </div>
        </div>
      </div>
    </Wrapper>
  );
}
