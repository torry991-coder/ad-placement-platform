import { useState, useCallback } from "react";

/**
 * Sync a value with localStorage.
 *
 * @param key - localStorage key.
 * @param initialValue - Fallback value used when the key isn't present
 *   or if parsing fails.
 * @returns A tuple of [storedValue, setValue] matching the useState API.
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item != null ? (JSON.parse(item) as T) : initialValue;
    } catch {
      // If JSON parsing fails, fall back to the initial value
      return initialValue;
    }
  });

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setStoredValue((prev) => {
        const nextValue =
          typeof value === "function"
            ? (value as (prev: T) => T)(prev)
            : value;
        try {
          window.localStorage.setItem(key, JSON.stringify(nextValue));
        } catch {
          // localStorage full or serialization error — silently ignore
        }
        return nextValue;
      });
    },
    [key]
  );

  return [storedValue, setValue];
}
