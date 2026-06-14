import clsx from "clsx";

interface SkeletonProps {
  className?: string;
  /** Preset shapes */
  variant?: "text" | "card" | "chart" | "table-row" | "circle";
}

export function Skeleton({ className, variant = "text" }: SkeletonProps) {
  if (variant === "card") {
    return (
      <div className={clsx("card p-5 animate-pulse space-y-3", className)}>
        <div className="h-4 w-2/3 bg-gray-200 dark:bg-gray-700 rounded" />
        <div className="h-8 w-1/2 bg-gray-200 dark:bg-gray-700 rounded" />
        <div className="h-3 w-1/3 bg-gray-100 dark:bg-gray-800 rounded" />
      </div>
    );
  }

  if (variant === "chart") {
    return (
      <div className={clsx("card p-5 animate-pulse space-y-4", className)}>
        <div className="h-4 w-1/3 bg-gray-200 dark:bg-gray-700 rounded" />
        <div className="h-[260px] bg-gray-100 dark:bg-gray-800 rounded" />
      </div>
    );
  }

  if (variant === "table-row") {
    return (
      <tr className="animate-pulse">
        {Array.from({ length: 5 }).map((_, i) => (
          <td key={i} className="px-6 py-4">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
          </td>
        ))}
      </tr>
    );
  }

  if (variant === "circle") {
    return (
      <div
        className={clsx(
          "rounded-full bg-gray-200 dark:bg-gray-700 animate-pulse",
          className || "w-10 h-10",
        )}
      />
    );
  }

  return (
    <div
      className={clsx(
        "h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse",
        className || "w-full",
      )}
    />
  );
}

/** Dashboard loading skeleton: full page layout */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="card p-5 space-y-3">
            <div className="h-3 w-20 bg-gray-200 dark:bg-gray-700 rounded" />
            <div className="h-7 w-28 bg-gray-200 dark:bg-gray-700 rounded" />
            <div className="h-3 w-14 bg-gray-100 dark:bg-gray-800 rounded" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5 space-y-4">
          <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-[260px] bg-gray-100 dark:bg-gray-800 rounded" />
        </div>
        <div className="card p-5 space-y-4">
          <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-[260px] bg-gray-100 dark:bg-gray-800 rounded" />
        </div>
      </div>
    </div>
  );
}
