import { useState, useEffect, useRef, useCallback } from "react";

export interface SSEState<T = Record<string, unknown>> {
  data: T | null;
  isConnected: boolean;
  error: Event | string | null;
  close: () => void;
}

/**
 * React hook for consuming Server-Sent Events.
 *
 * @param url - The SSE endpoint URL.
 * @returns { data, isConnected, error, close }
 *
 * - `data` — the most recent parsed event payload.
 * - `isConnected` — whether the EventSource is open.
 * - `error` — the last error (Event object or string).
 * - `close()` — manually close the connection.
 *
 * Features:
 * - Auto-reconnect on connection loss (EventSource built-in).
 * - Parses `event:`, `data:`, and `id:` fields from SSE.
 * - Handles `event: done` to auto-close.
 * - Cleans up on unmount.
 */
export function useSSE<T = Record<string, unknown>>(
  url: string
): SSEState<T> {
  const [data, setData] = useState<T | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Event | string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const close = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    // Don't open a connection for an empty URL
    if (!url) return;

    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    es.onmessage = (e: MessageEvent) => {
      try {
        const parsed = JSON.parse(e.data);
        setData(parsed as T);
      } catch {
        // If data isn't JSON, store it as-is inside a wrapper
        setData(e.data as unknown as T);
      }
    };

    // Listen for named events — some backends send `event: done`
    es.addEventListener("done", () => {
      close();
    });

    // Generic error handler (fired on connection errors etc.)
    es.onerror = (e: Event) => {
      // The browser sets readyState=CLOSED on unrecoverable errors;
      // otherwise EventSource will auto-reconnect.
      if (es.readyState === EventSource.CLOSED) {
        setIsConnected(false);
      }
      setError(e);
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    };
  }, [url, close]);

  return { data, isConnected, error, close };
}
