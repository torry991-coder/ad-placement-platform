import { useEffect, useRef, useState } from "react";
import { Search, ArrowRight, CornerDownLeft } from "lucide-react";
import clsx from "clsx";

interface Command {
  id: string;
  label: string;
  path?: string;
  action?: () => void;
  keys?: string;
  category?: string;
}

interface Props {
  open: boolean;
  onClose: () => void;
  query: string;
  onQueryChange: (q: string) => void;
  commands: Command[];
  onNavigate: (path: string) => void;
}

export function CommandPalette({
  open,
  onClose,
  query,
  onQueryChange,
  commands,
  onNavigate,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
      setSelected(0);
    }
  }, [open]);

  useEffect(() => {
    setSelected(0);
  }, [query]);

  const execute = (cmd: Command) => {
    if (cmd.path) {
      onNavigate(cmd.path);
    } else if (cmd.action) {
      cmd.action();
    }
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, commands.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (commands[selected]) execute(commands[selected]);
    } else if (e.key === "Escape") {
      onClose();
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Dialog */}
      <div className="relative w-full max-w-lg mx-4 bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-gray-200 dark:border-slate-700 overflow-hidden animate-fade-in-up">
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100 dark:border-slate-700">
          <Search size={18} className="text-gray-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="搜索页面或输入命令..."
            className="flex-1 bg-transparent text-sm outline-none text-gray-900 dark:text-white placeholder:text-gray-400"
          />
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-gray-400">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-72 overflow-y-auto p-2">
          {commands.length === 0 ? (
            <div className="py-8 text-center text-sm text-gray-400">未找到匹配命令</div>
          ) : (
            commands.map((cmd, idx) => (
              <button
                key={cmd.id}
                onClick={() => execute(cmd)}
                className={clsx(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors",
                  idx === selected
                    ? "bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300"
                    : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700",
                )}
              >
                <span className="flex-1 text-sm font-medium">{cmd.label}</span>
                <span className="text-[10px] text-gray-400">{cmd.category}</span>
                {cmd.keys && (
                  <kbd className="hidden sm:inline text-[10px] font-mono text-gray-400 bg-gray-100 dark:bg-slate-700 px-1.5 py-0.5 rounded">
                    {cmd.keys}
                  </kbd>
                )}
                {idx === selected && <CornerDownLeft size={14} className="text-gray-400 shrink-0" />}
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-gray-100 dark:border-slate-700 text-[10px] text-gray-400">
          <span className="flex items-center gap-1">
            <kbd className="px-1 py-0.5 rounded bg-gray-100 dark:bg-slate-700">↑↓</kbd> 导航
          </span>
          <span className="flex items-center gap-1">
            <kbd className="px-1 py-0.5 rounded bg-gray-100 dark:bg-slate-700">↵</kbd> 选择
          </span>
          <span className="flex items-center gap-1">
            <kbd className="px-1 py-0.5 rounded bg-gray-100 dark:bg-slate-700">Esc</kbd> 关闭
          </span>
        </div>
      </div>
    </div>
  );
}
