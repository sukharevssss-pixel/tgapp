import React, { useEffect, useState } from "react";

export default function Chests({ user, apiRoot, onBalanceChange }) {
  const [chests, setChests] = useState([]);
  const [msg, setMsg] = useState("");
  const [loadingChest, setLoadingChest] = useState(null); // ID сундука, который открывается

  const fetchChests = async () => {
    try {
      const res = await fetch(`${apiRoot}/api/chests`);
      const data = await res.json();
      setChests(data || []);
    } catch (e) {
      console.error("Ошибка загрузки сундуков:", e);
    }
  };

  useEffect(() => {
    fetchChests();
  }, []);

  const openChest = async (chest_id) => {
    setMsg("");
    setLoadingChest(chest_id); // Блокируем кнопку

    if (!user || !user.telegram_id) {
      setMsg("Ошибка: пользователь не найден");
      setLoadingChest(null);
      return;
    }

    try {
      const res = await fetch(`${apiRoot}/api/chests/open`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ telegram_id: user.telegram_id, chest_id }),
      });

      const data = await res.json();
      if (!res.ok) {
        setMsg(data.detail || "Произошла ошибка");
      } else {
        setMsg(`🎉 Выпало: ${data.reward} монет!`);
        
        // Вызываем функцию из родительского компонента для обновления баланса
        if (onBalanceChange) {
          onBalanceChange();
        }
      }
    } catch (e) {
      setMsg(String(e));
    } finally {
      setLoadingChest(null); // Разблокируем кнопку
    }
  };

  return (
    <div>
      <h2>Сундуки</h2>

      <div className="small" style={{ marginBottom: 12 }}>
        Ваш баланс: {user?.balance ?? 0} монет
      </div>

      <div>
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
              <button 
                className="btn" 
                onClick={() => openChest(c.id)}
                disabled={loadingChest === c.id} // Кнопка неактивна во время загрузки
              >
                {loadingChest === c.id ? "Открываем..." : "Открыть"}
              </button>
            </div>
          </div>
        ))}
      </div>

      {msg && (
        <div style={{ marginTop: 10, fontWeight: 600 }} className={msg.includes("Ошибка") ? "error" : "success"}>
          {msg}
        </div>
      )}
    </div>
  );
}
