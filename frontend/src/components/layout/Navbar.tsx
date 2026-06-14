import React, { createElement } from "react";
import { Sun, Moon, Bell, Monitor } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useDarkMode } from "../../hooks/useDarkMode";

export default function Navbar() {
  const navigate = useNavigate();
  const { theme, setTheme, isDark } = useDarkMode();

  const cycleTheme = () => {
    if (theme === "light") setTheme("dark");
    else if (theme === "dark") setTheme("system");
    else setTheme("light");
  };

  const themeIcon = theme === "system" ? Monitor : isDark ? Sun : Moon;
  const themeHint = theme === "system" ? "跟随系统" : isDark ? "切换浅色" : "切换深色";

  return (
    <header className="h-16 bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 flex items-center justify-between px-6 sticky top-0 z-10 backdrop-blur-sm bg-white/80 dark:bg-slate-800/80">
      <div>
        <h1 className="text-lg font-semibold text-gray-900 dark:text-white tracking-tight">
          智能广告投放系统
        </h1>
        <p className="text-xs text-gray-400">
          Enterprise Ad Placement Platform
        </p>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => navigate("/alerts")}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400 relative transition-colors"
          title="告警中心"
        >
          <Bell size={20} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full animate-pulse" />
        </button>

        <button
          onClick={cycleTheme}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400 transition-colors"
          title={themeHint}
        >
          {React.createElement(themeIcon, { size: 20 })}
        </button>
      </div>
    </header>
  );
}
