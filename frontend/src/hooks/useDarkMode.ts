import { useEffect, useState, useCallback } from "react";

type Theme = "light" | "dark" | "system";

const STORAGE_KEY = "ad-platform-theme";

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function getStoredTheme(): Theme {
  if (typeof window === "undefined") return "system";
  return (localStorage.getItem(STORAGE_KEY) as Theme) || "system";
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  const resolved = theme === "system" ? getSystemTheme() : theme;

  if (resolved === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }

  // Store for instant load on next visit (avoids flash)
  localStorage.setItem(STORAGE_KEY, theme);
}

export function useDarkMode() {
  const [theme, setThemeState] = useState<Theme>(getStoredTheme);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    applyTheme(t);
  }, []);

  const toggle = useCallback(() => {
    const resolved = theme === "system" ? getSystemTheme() : theme;
    const next = resolved === "dark" ? "light" : "dark";
    setThemeState(next);
    applyTheme(next);
  }, [theme]);

  // Apply on mount
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // Listen for system changes
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      if (theme === "system") applyTheme("system");
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  const resolved = theme === "system" ? getSystemTheme() : theme;

  return { theme, resolved, setTheme, toggle, isDark: resolved === "dark" };
}
