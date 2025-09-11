import React, { useEffect, useState } from "react";

export default function DebugUser() {
  const [data, setData] = useState(null);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      setData({
        initData: tg.initData,
        initDataUnsafe: tg.initDataUnsafe,
      });
    } else {
      setData({ error: "❌ Telegram.WebApp не найден" });
    }
  }, []);

  return (
    <div style={{ padding: 10, background: "#222", color: "#0f0" }}>
      <h3>Debug Info</h3>
      <pre style={{ whiteSpace: "pre-wrap", fontSize: "12px" }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}
