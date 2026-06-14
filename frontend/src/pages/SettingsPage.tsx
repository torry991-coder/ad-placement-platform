import { useState, useEffect } from "react";
import { Save, Server, CheckCircle2, Zap, Globe, Cpu, Bot } from "lucide-react";
import { api } from "../services/api";

interface ProviderInfo {
  id: string;
  name: string;
  models: string[];
  description: string;
  configured: boolean;
  current: boolean;
}

interface LLMSettings {
  provider: string;
  model: string;
  providers: ProviderInfo[];
}

const PROVIDER_ICONS: Record<string, React.ReactNode> = {
  deepseek: <Zap size={18} />,
  openai: <Globe size={18} />,
  google: <Globe size={18} />,
  ollama: <Cpu size={18} />,
  fallback: <Bot size={18} />,
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<LLMSettings | null>(null);
  const [provider, setProvider] = useState("auto");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Simulator
  const [simQps, setSimQps] = useState(1000);
  const [simCampaigns, setSimCampaigns] = useState(50);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const { data } = await api.get<LLMSettings>("/api/llm/settings");
      setSettings(data);
      setProvider(data.provider);
      setModel(data.model);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load settings");
    } finally {
      setLoading(false);
    }
  };

  const handleProviderChange = (p: string) => {
    setProvider(p);
    const prov = settings?.providers.find((x) => x.id === p);
    if (prov) setModel(prov.models[0]);
    setApiKey("");
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      const payload: any = { provider, model };
      if (apiKey) payload.api_key = apiKey;
      const { data } = await api.post<LLMSettings>("/api/llm/settings", payload);
      setSettings(data);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in-up max-w-4xl">
      <div>
        <h2 className="text-2xl font-bold">系统设置</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          选择 AI 模型提供商和配置参数
        </p>
      </div>

      {error && (
        <div className="px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6">
        {/* LLM Provider Selection */}
        <div className="card p-6 space-y-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/30">
              <Zap size={18} className="text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h3 className="font-semibold">AI 模型</h3>
              <p className="text-xs text-gray-400">选择对话和智能分析使用的 LLM</p>
            </div>
          </div>

          {/* Provider Tabs */}
          <div className="flex flex-wrap gap-2">
            {(settings?.providers || []).map((p) => (
              <button
                key={p.id}
                onClick={() => handleProviderChange(p.id)}
                className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-all
                  ${provider === p.id
                    ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300"
                    : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:border-gray-300"
                  }
                `}
              >
                <span className={provider === p.id ? "text-indigo-600 dark:text-indigo-400" : ""}>
                  {PROVIDER_ICONS[p.id]}
                </span>
                {p.name}
                {p.configured && (
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" title="已配置" />
                )}
              </button>
            ))}
          </div>

          {/* Description */}
          {settings?.providers.find((p) => p.id === provider) && (
            <p className="text-xs text-gray-400 bg-gray-50 dark:bg-gray-800/50 px-3 py-2 rounded-lg">
              {settings.providers.find((p) => p.id === provider)!.description}
            </p>
          )}

          {/* Model Dropdown */}
          <div>
            <label className="block text-sm font-medium mb-1.5">模型</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {(settings?.providers.find((p) => p.id === provider)?.models || []).map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          {/* API Key */}
          {provider !== "fallback" && provider !== "auto" && (
            <div>
              <label className="block text-sm font-medium mb-1.5">
                {settings?.providers.find((p) => p.id === provider)?.name} API Key
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={provider === "deepseek" ? "sk-..." : "输入 API Key"}
                className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 transition-shadow"
              />
            </div>
          )}
        </div>

        {/* Simulator Config */}
        <div className="card p-6 space-y-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/30">
              <Server size={18} className="text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <h3 className="font-semibold">模拟数据配置</h3>
              <p className="text-xs text-gray-400">开发测试用</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">模拟拍卖 QPS</label>
              <input
                type="number"
                value={simQps}
                onChange={(e) => setSimQps(Number(e.target.value))}
                min={10}
                max={100000}
                className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">模拟活动数量</label>
              <input
                type="number"
                value={simCampaigns}
                onChange={(e) => setSimCampaigns(Number(e.target.value))}
                min={1}
                max={1000}
                className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Save */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center gap-2 px-6 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-all font-medium text-sm disabled:opacity-50 active:scale-95"
        >
          {saving ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              保存中...
            </>
          ) : saved ? (
            <>
              <CheckCircle2 size={16} />
              已保存
            </>
          ) : (
            <>
              <Save size={16} />
              保存设置
            </>
          )}
        </button>
      </div>
    </div>
  );
}
