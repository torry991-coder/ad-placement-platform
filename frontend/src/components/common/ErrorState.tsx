import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({
  message = "加载失败，请稍后重试",
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="p-4 rounded-full bg-red-50 dark:bg-red-900/20 mb-4">
        <AlertTriangle size={36} className="text-red-500 dark:text-red-400 opacity-80" />
      </div>
      <h3 className="text-base font-semibold text-gray-700 dark:text-gray-300 mb-1">
        出错了
      </h3>
      <p className="text-sm text-gray-400 dark:text-gray-500 max-w-sm mb-4">
        {message}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors"
        >
          <RefreshCw size={14} />
          重试
        </button>
      )}
    </div>
  );
}
