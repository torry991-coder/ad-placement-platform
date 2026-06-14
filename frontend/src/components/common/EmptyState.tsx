import { type LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      {Icon && (
        <div className="p-4 rounded-full bg-gray-100 dark:bg-gray-800 mb-4">
          <Icon size={36} className="text-gray-400 dark:text-gray-500 opacity-60" />
        </div>
      )}
      <h3 className="text-base font-semibold text-gray-700 dark:text-gray-300 mb-1">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-gray-400 dark:text-gray-500 max-w-sm mb-4">
          {description}
        </p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 text-sm font-medium bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
