import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Megaphone,
  Palette,
  FlaskConical,
  Bell,
  Settings,
  ChevronLeft,
  ChevronRight,
  Users,
  Bot,
  Monitor,
  FileText,
} from "lucide-react";
import { useState } from "react";
import clsx from "clsx";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "仪表盘" },
  { to: "/campaigns", icon: Megaphone, label: "广告活动" },
  { to: "/creative", icon: Palette, label: "创意管理" },
  { to: "/experiments", icon: FlaskConical, label: "实验" },
  { to: "/audience", icon: Users, label: "受众分析" },
  { to: "/reports", icon: FileText, label: "数据报表" },
  { to: "/alerts", icon: Bell, label: "告警" },
  { to: "/bigscreen", icon: Monitor, label: "数据大屏" },
  { to: "/ai-agent", icon: Bot, label: "AI助手" },
  { to: "/settings", icon: Settings, label: "系统设置" },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={clsx(
        "h-screen sticky top-0 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col transition-all duration-200",
        collapsed ? "w-16" : "w-56"
      )}
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-4 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center flex-shrink-0">
            <Megaphone className="w-4 h-4 text-white" />
          </div>
          {!collapsed && (
            <span className="font-semibold text-sm whitespace-nowrap">
              智能投放
            </span>
          )}
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="ml-auto p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400"
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 space-y-1 px-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-400"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
              )
            }
          >
            <item.icon size={20} className="flex-shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      {!collapsed && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-800">
          <p className="text-xs text-gray-400">v1.0.0 · Enterprise</p>
        </div>
      )}
    </aside>
  );
}
