import { useState, useEffect } from "react";

/**
 * Debounce a value by the specified delay (ms).
 *
 * Returns the debounced value which only updates after `delay`
 * milliseconds of inactivity on the input value.
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    // Set up a timer to update the debounced value after `delay` ms
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    // If the value changes before the delay expires, clear the timer
    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}
