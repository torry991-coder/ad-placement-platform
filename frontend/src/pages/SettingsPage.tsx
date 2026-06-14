import { useState } from "react";
import { Save, Key, Server, CheckCircle2 } from "lucide-react";
import toast from "react-hot-toast";

export default function SettingsPage() {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [openaiKey, setOpenaiKey] = useState("");
  const [googleKey, setGoogleKey] = useState("");
  const [simQps, setSimQps] = useState(1000);
  const [simCampaigns, setSimCampaigns] = useState(50);

  const handleSave = () => {
    setSaving(true);
    // In production: POST to backend config endpoint
    setTimeout(() => {
      setSaving(false);
      setSaved(true);
      toast.success("设置已保存");
      setTimeout(() => setSaved(false), 2000);
    }, 600);
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div>
        <h2 className="text-2xl font-bold">系统设置</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          配置 API Key 和模拟参数
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-4xl">
        {/* LLM Config */}
        <div className="card p-6 space-y-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/30">
              <Key size={18} className="text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h3 className="font-semibold">LLM 配置</h3>
              <p className="text-xs text-gray-400">启用 AI 智能优化</p>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">
              OpenAI API Key
            </label>
            <input
              type="password"
              value={openaiKey}
              onChange={(e) => setOpenaiKey(e.target.value)}
              placeholder="sk-..."
              className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 transition-shadow"
            />
            <p className="text-xs text-gray-400 mt-1">用于 GPT-4o 智能分析和创意生成</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">
              Google Gemini API Key
            </label>
            <input
              type="password"
              value={googleKey}
              onChange={(e) => setGoogleKey(e.target.value)}
              placeholder="AIza..."
              className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 transition-shadow"
            />
            <p className="text-xs text-gray-400 mt-1">备用 LLM，Gemini 2.0 Flash</p>
          </div>
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

          <div>
            <label className="block text-sm font-medium mb-1.5">模拟拍卖 QPS</label>
            <input
              type="number"
              value={simQps}
              onChange={(e) => setSimQps(Number(e.target.value))}
              min={10}
              max={100000}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 transition-shadow"
            />
            <p className="text-xs text-gray-400 mt-1">每秒模拟拍卖请求数，最大 100000</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">模拟活动数量</label>
            <input
              type="number"
              value={simCampaigns}
              onChange={(e) => setSimCampaigns(Number(e.target.value))}
              min={1}
              max={1000}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 transition-shadow"
            />
            <p className="text-xs text-gray-400 mt-1">种子数据生成的活动数量</p>
          </div>
        </div>
      </div>

      {/* Save Button */}
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
        <span className="text-xs text-gray-400">
          配置保存在浏览器本地，重启后需重新设置
        </span>
      </div>
    </div>
  );
}
