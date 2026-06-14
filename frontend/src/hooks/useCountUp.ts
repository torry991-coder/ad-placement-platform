import { useEffect, useRef, useState } from "react";

interface UseCountUpOptions {
  end: number;
  duration?: number;   // ms
  start?: number;
  enabled?: boolean;
  formatter?: (val: number) => string;
}

export function useCountUp({
  end,
  duration = 1000,
  start = 0,
  enabled = true,
  formatter,
}: UseCountUpOptions) {
  const [value, setValue] = useState(start);
  const raf = useRef<number>(0);
  const startTime = useRef<number>(0);

  useEffect(() => {
    if (!enabled) {
      setValue(end);
      return;
    }

    const range = end - start;
    if (range === 0) {
      setValue(end);
      return;
    }

    startTime.current = performance.now();

    const animate = (now: number) => {
      const elapsed = now - startTime.current;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(start + range * eased);

      if (progress < 1) {
        raf.current = requestAnimationFrame(animate);
      }
    };

    raf.current = requestAnimationFrame(animate);

    return () => cancelAnimationFrame(raf.current);
  }, [end, start, duration, enabled]);

  return formatter ? formatter(value) : Math.round(value);
}
