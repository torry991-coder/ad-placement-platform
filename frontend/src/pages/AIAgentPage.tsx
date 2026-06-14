import { useState, useRef, useEffect, useCallback } from "react";
import { Bot, Send, Sparkles, X, Loader2, Zap } from "lucide-react";
import { api } from "../services/api";
import clsx from "clsx";

// ── Types ────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  suggestions?: string[];
  timestamp: string;
}

interface CampaignOption {
  id: number;
  name: string;
}

// ── Component ────────────────────────────────────────────────────────────────

export default function AIAgentPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "你好！我是智能广告投放助手，可以帮你分析广告数据、优化出价策略、生成投放建议。请问有什么可以帮你的？",
      suggestions: [
        "分析当前广告投放效果",
        "优化ROAS出价策略",
        "推荐受众定向方案",
        "检测异常花费",
      ],
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Campaign selector
  const [campaigns, setCampaigns] = useState<CampaignOption[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<number | null>(
    null
  );
  const [campaignsLoading, setCampaignsLoading] = useState(false);

  // SSE stream mode
  const [streamMode, setStreamMode] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // ── Fetch campaigns ──────────────────────────────────────────────────────

  useEffect(() => {
    const fetchCampaigns = async () => {
      setCampaignsLoading(true);
      try {
        const res = await api.get("/api/campaigns/");
        const list = res.data?.data || res.data || [];
        setCampaigns(Array.isArray(list) ? list : []);
      } catch {
        // Non-critical, silently fail
      } finally {
        setCampaignsLoading(false);
      }
    };
    fetchCampaigns();
  }, []);

  // ── Scroll to bottom ─────────────────────────────────────────────────────

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Helpers ──────────────────────────────────────────────────────────────

  const generateId = () =>
    `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

  const formatTime = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  };

  // ── Send message (regular) ───────────────────────────────────────────────

  const sendRegular = useCallback(
    async (userMessage: string) => {
      const userMsg: Message = {
        id: generateId(),
        role: "user",
        content: userMessage,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      setLoading(true);
      setError(null);

      try {
        const payload: { message: string; campaign_id?: number } = {
          message: userMessage,
        };
        if (selectedCampaignId) {
          payload.campaign_id = selectedCampaignId;
        }

        const res = await api.post("/api/agent/chat", payload);
        const data = res.data?.data || res.data;

        const assistantMsg: Message = {
          id: generateId(),
          role: "assistant",
          content: data?.reply || data?.content || "抱歉，我暂时无法处理这个请求。",
          suggestions: data?.suggestions || [],
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response
            ?.data?.detail || "请求失败，请稍后重试";
        setError(msg);
        const errorMsg: Message = {
          id: generateId(),
          role: "assistant",
          content: `❌ ${msg}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setLoading(false);
      }
    },
    [selectedCampaignId]
  );

  // ── Send message (SSE stream) ────────────────────────────────────────────

  const sendStream = useCallback(
    async (userMessage: string) => {
      const userMsg: Message = {
        id: generateId(),
        role: "user",
        content: userMessage,
        timestamp: new Date().toISOString(),
      };
      const assistantId = generateId();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);

      setLoading(true);
      setError(null);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const params = new URLSearchParams();
        params.set("message", userMessage);
        if (selectedCampaignId) {
          params.set("campaign_id", String(selectedCampaignId));
        }

        const url = `/api/agent/stream?${params.toString()}`;
        const response = await fetch(url, {
          signal: controller.signal,
          headers: { Accept: "text/event-stream" },
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("无法读取流");

        const decoder = new TextDecoder();
        let accumulated = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6).trim();
              if (data === "[DONE]") continue;

              try {
                const parsed = JSON.parse(data);
                if (parsed.content) {
                  accumulated += parsed.content;
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantId
                        ? { ...m, content: accumulated }
                        : m
                    )
                  );
                }
                if (parsed.suggestions) {
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantId
                        ? { ...m, suggestions: parsed.suggestions }
                        : m
                    )
                  );
                }
              } catch {
                // Non-JSON data — treat as raw content
                accumulated += data;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, content: accumulated }
                      : m
                  )
                );
              }
            }
          }
        }

        // Ensure it's not empty
        if (!accumulated) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: "收到空响应，请重试。" }
                : m
            )
          );
        }
      } catch (err: unknown) {
        if ((err as Error).name === "AbortError") {
          // User cancelled — no error needed
        } else {
          const msg =
            (err as Error).message || "流式请求失败";
          setError(msg);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId && !m.content
                ? { ...m, content: `❌ ${msg}` }
                : m
            )
          );
        }
      } finally {
        setLoading(false);
        abortControllerRef.current = null;
      }
    },
    [selectedCampaignId]
  );

  // ── Handle submit ────────────────────────────────────────────────────────

  const handleSubmit = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    setInput("");

    if (streamMode) {
      await sendStream(trimmed);
    } else {
      await sendRegular(trimmed);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // ── Handle suggestion click ──────────────────────────────────────────────

  const handleSuggestion = (suggestion: string) => {
    setInput(suggestion);
    inputRef.current?.focus();
  };

  // ── Cancel stream ────────────────────────────────────────────────────────

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  // ── Clear chat ───────────────────────────────────────────────────────────

  const handleClear = () => {
    setMessages([
      {
        id: "welcome",
        role: "assistant",
        content:
          "你好！我是智能广告投放助手，可以帮你分析广告数据、优化出价策略、生成投放建议。请问有什么可以帮你的？",
        suggestions: [
          "分析当前广告投放效果",
          "优化ROAS出价策略",
          "推荐受众定向方案",
          "检测异常花费",
        ],
        timestamp: new Date().toISOString(),
      },
    ]);
    setError(null);
  };

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Bot size={24} className="text-brand-500" />
            AI 智能助手
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            与 AI 对话，获取广告投放智能分析与优化建议
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Campaign selector */}
          <select
            value={selectedCampaignId ?? ""}
            onChange={(e) =>
              setSelectedCampaignId(
                e.target.value ? Number(e.target.value) : null
              )
            }
            className="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">全部活动</option>
            {campaigns.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          {/* Stream toggle */}
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <div
              className={clsx(
                "relative w-9 h-5 rounded-full transition-colors",
                streamMode
                  ? "bg-brand-500"
                  : "bg-gray-300 dark:bg-gray-600"
              )}
              onClick={() => setStreamMode(!streamMode)}
            >
              <div
                className={clsx(
                  "absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform",
                  streamMode ? "translate-x-[18px]" : "translate-x-0.5"
                )}
              />
            </div>
            <span className="text-gray-500">
              <Zap size={14} className="inline mr-1" />
              流式
            </span>
          </label>

          <button
            onClick={handleClear}
            className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 underline"
          >
            清空对话
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex-shrink-0 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-3 underline hover:no-underline"
          >
            关闭
          </button>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={clsx(
              "flex gap-3 max-w-[85%]",
              msg.role === "user" ? "ml-auto flex-row-reverse" : ""
            )}
          >
            {/* Avatar */}
            <div
              className={clsx(
                "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
                msg.role === "assistant"
                  ? "bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400"
                  : "bg-gray-200 dark:bg-gray-700 text-gray-500"
              )}
            >
              {msg.role === "assistant" ? (
                <Bot size={16} />
              ) : (
                <span className="text-xs font-bold">我</span>
              )}
            </div>

            {/* Bubble */}
            <div className="space-y-2 min-w-0">
              <div
                className={clsx(
                  "px-4 py-3 rounded-xl text-sm leading-relaxed whitespace-pre-wrap break-words",
                  msg.role === "assistant"
                    ? "bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700"
                    : "bg-brand-600 text-white"
                )}
              >
                {msg.content || (
                  <span className="inline-flex items-center gap-2 text-gray-400">
                    <Loader2 size={14} className="animate-spin" />
                    思考中...
                  </span>
                )}
              </div>

              {/* Suggestions */}
              {msg.suggestions && msg.suggestions.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {msg.suggestions.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => handleSuggestion(s)}
                      className="px-3 py-1.5 text-xs rounded-full border border-brand-200 dark:border-brand-800 text-brand-700 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20 hover:bg-brand-100 dark:hover:bg-brand-900/40 transition-colors"
                    >
                      <Sparkles size={12} className="inline mr-1" />
                      {s}
                    </button>
                  ))}
                </div>
              )}

              {/* Timestamp */}
              <p
                className={clsx(
                  "text-xs text-gray-400",
                  msg.role === "user" ? "text-right" : ""
                )}
              >
                {formatTime(msg.timestamp)}
              </p>
            </div>
          </div>
        ))}

        {/* Loading indicator for regular mode */}
        {loading && !streamMode && messages[messages.length - 1]?.role === "user" && (
          <div className="flex gap-3 max-w-[85%]">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-brand-100 dark:bg-brand-900/30 text-brand-600">
              <Bot size={16} />
            </div>
            <div className="px-4 py-3 rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
              <Loader2 size={16} className="animate-spin text-gray-400" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="flex-shrink-0">
        <div className="flex items-end gap-3">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入你的问题，例如：分析昨天的ROAS..."
              disabled={loading && !streamMode}
              className="w-full px-4 py-3 pr-12 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
            />
          </div>

          {loading && streamMode ? (
            <button
              onClick={handleCancel}
              className="flex-shrink-0 p-3 rounded-xl bg-red-500 text-white hover:bg-red-600 transition-colors"
              title="停止生成"
            >
              <X size={20} />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!input.trim() || loading}
              className="flex-shrink-0 p-3 rounded-xl bg-brand-600 text-white hover:bg-brand-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              title="发送"
            >
              <Send size={20} />
            </button>
          )}
        </div>
        <p className="text-xs text-gray-400 mt-2 text-center">
          按 Enter 发送消息 · AI 生成内容仅供参考，请结合实际情况判断
        </p>
      </div>
    </div>
  );
}
