import { useEffect, useCallback, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";

interface Shortcut {
  keys: string;         // e.g. "ctrl+k", "shift+a"
  description: string;
  action: () => void;
  category?: string;
}

interface UseKeyboardShortcutsOptions {
  shortcuts: Shortcut[];
  enabled?: boolean;
}

/** Parse "ctrl+k" into {ctrl: true, key: "k"} */
function parseShortcut(keys: string): {
  ctrl: boolean;
  shift: boolean;
  alt: boolean;
  key: string;
} {
  const parts = keys.toLowerCase().split("+");
  return {
    ctrl: parts.includes("ctrl"),
    shift: parts.includes("shift"),
    alt: parts.includes("alt"),
    key: parts.filter((p) => !["ctrl", "shift", "alt"].includes(p)).join("+"),
  };
}

export function useKeyboardShortcuts({
  shortcuts,
  enabled = true,
}: UseKeyboardShortcutsOptions) {
  useEffect(() => {
    if (!enabled) return;

    const handler = (e: KeyboardEvent) => {
      // Don't trigger inside inputs/textareas/selects
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      for (const s of shortcuts) {
        const parsed = parseShortcut(s.keys);
        if (
          e.ctrlKey === parsed.ctrl &&
          e.shiftKey === parsed.shift &&
          e.altKey === parsed.alt &&
          e.key.toLowerCase() === parsed.key
        ) {
          e.preventDefault();
          s.action();
          return;
        }
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [shortcuts, enabled]);
}

/** Global command palette hook (Ctrl+K search) */
export function useCommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const commands = [
    { id: "dashboard", label: "仪表盘", path: "/", keys: "G D", category: "导航" },
    { id: "campaigns", label: "活动管理", path: "/campaigns", keys: "G C", category: "导航" },
    { id: "creative", label: "创意管理", path: "/creative", keys: "G R", category: "导航" },
    { id: "audience", label: "受众分析", path: "/audience", keys: "G A", category: "导航" },
    { id: "experiments", label: "A/B实验", path: "/experiments", keys: "G E", category: "导航" },
    { id: "reports", label: "数据报表", path: "/reports", keys: "G P", category: "导航" },
    { id: "alerts", label: "告警中心", path: "/alerts", keys: "G L", category: "导航" },
    { id: "ai-agent", label: "AI助手", path: "/ai-agent", keys: "G I", category: "导航" },
    { id: "settings", label: "系统设置", path: "/settings", keys: "G S", category: "导航" },
    { id: "refresh", label: "刷新数据", action: () => window.location.reload(), keys: "Ctrl+R", category: "操作" },
  ];

  const filtered = query
    ? commands.filter(
        (c) =>
          c.label.toLowerCase().includes(query.toLowerCase()) ||
          c.category?.toLowerCase().includes(query.toLowerCase()),
      )
    : commands;

  useKeyboardShortcuts({
    shortcuts: [
      {
        keys: "ctrl+k",
        description: "打开命令面板",
        action: () => setOpen((v) => !v),
      },
    ],
  });

  return { open, setOpen, query, setQuery, commands: filtered, navigate };
}
