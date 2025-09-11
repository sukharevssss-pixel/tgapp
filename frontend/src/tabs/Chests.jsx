import React, { useEffect, useState } from "react";

export default function Chests({ user, apiRoot }) {
  const [chests, setChests] = useState([]);
  const [msg, setMsg] = useState("");

  const fetchChests = async () => {
    try {
      const res = await fetch(`${apiRoot}/api/chests`);
      const data = await res.json();
      setChests(data || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchChests();
  }, []);

  const openChest = async (chest_id) => {
    setMsg("");

    if (!user || !user.telegram_id) {
      setMsg("Ошибка: пользователь не найден");
      return;
    }

    try {
      const res = await fetch(`${apiRoot}/api/chests/open`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ telegram_id: user.telegram_id, chest_id }),
      });

      if (!res.ok) {
        const jd = await res.json();
        setMsg(jd.detail || "Ошибка");
      } else {
        const data = await res.json();
        setMsg(`Выпало: ${data.reward} монет!`);
      }

      fetchChests();
    } catch (e) {
      setMsg(String(e));
    }
  };

  return (
    <div>
      <h2>Сундуки</h2>

      <div className="small">
        Баланс: {user && user.balance !== undefined ? user.balance : 0} монет
      </div>

      <div style={{ marginTop: 12 }}>
        {chests.map((c) => (
          <div
            key={c.id}
            className="poll"
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontWeight: 600 }}>{c.name}</div>
              <div className="small">
                Цена: {c.price} — Награда: {c.reward_min}–{c.reward_max}
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn" onClick={() => openChest(c.id)}>
                Открыть
              </button>
            </div>
          </div>
        ))}
      </div>

      {msg && (
        <div style={{ marginTop: 10 }} className="success">
          {msg}
        </div>
      )}
    </div>
  );
}
