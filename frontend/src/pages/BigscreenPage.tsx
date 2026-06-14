import { useEffect, useState } from "react";

export default function BigscreenPage() {
  const [time, setTime] = useState(new Date());
  const [kpi, setKpi] = useState<any>(null);

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    fetch("/api/analytics/dashboard")
      .then((r) => r.json())
      .then(setKpi)
      .catch(() => {});
  }, []);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "#0a0a1a",
        color: "#fff",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "system-ui, sans-serif",
        gap: 20,
      }}
    >
      <h1 style={{ fontSize: 48, fontWeight: 700 }}>智能广告投放系统</h1>
      <h2 style={{ fontSize: 24, color: "#60a5fa" }}>实时数据大屏</h2>
      <p style={{ fontSize: 48, fontFamily: "monospace", color: "#60a5fa" }}>
        {String(time.getHours()).padStart(2, "0")}:
        {String(time.getMinutes()).padStart(2, "0")}:
        {String(time.getSeconds()).padStart(2, "0")}
      </p>
      {kpi && (
        <div style={{ display: "flex", gap: 40, marginTop: 20 }}>
          <div style={{ textAlign: "center" }}>
            <p style={{ color: "#9ca3af", fontSize: 14 }}>活跃活动</p>
            <p style={{ fontSize: 36, fontWeight: 700 }}>{kpi.active_campaigns}</p>
          </div>
          <div style={{ textAlign: "center" }}>
            <p style={{ color: "#9ca3af", fontSize: 14 }}>展示量</p>
            <p style={{ fontSize: 36, fontWeight: 700 }}>
              {(kpi.total_impressions / 10000).toFixed(0)}万
            </p>
          </div>
          <div style={{ textAlign: "center" }}>
            <p style={{ color: "#9ca3af", fontSize: 14 }}>ROAS</p>
            <p style={{ fontSize: 36, fontWeight: 700, color: "#34d399" }}>
              {kpi.avg_roas?.toFixed(2)}x
            </p>
          </div>
        </div>
      )}
      <div style={{ position: "absolute", bottom: 20, color: "#4b5563", fontSize: 12 }}>
        智能广告投放系统 v1.0 · 数据实时刷新
      </div>
    </div>
  );
}
