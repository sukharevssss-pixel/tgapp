import React, { useEffect, useState, useRef } from "react";
import Fireworks from "./Fireworks"; // ✨ Импортируем наш новый компонент

// ... (остальной код остается прежним до компонента)

export default function Chests({ user, apiRoot, onBalanceChange }) {
  const [chests, setChests] = useState([]);
  const [msg, setMsg] = useState("");
  const [animationState, setAnimationState] = useState({ id: null, reward: null, spinning: false });
  const [showFireworks, setShowFireworks] = useState(false); // ✨ Новое состояние для салюта

  const animationTimeoutRef = useRef(null);

  useEffect(() => { /* ... без изменений ... */ }, []);
  const fetchChests = async () => { /* ... без изменений ... */ };

  const openChest = async (chest_id) => {
    // ... (начало функции без изменений) ...
    setMsg("");
    setShowFireworks(false); // Убираем старый салют
    if (animationTimeoutRef.current) clearTimeout(animationTimeoutRef.current);

    if (!user || !user.telegram_id) {
      setMsg("Ошибка: пользователь не найден");
      return;
    }

    setAnimationState({ id: chest_id, reward: null, spinning: true });

    try {
      const res = await fetch(`${apiRoot}/api/chests/open`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ telegram_id: user.telegram_id, chest_id }),
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Произошла ошибка");
      }

      setAnimationState({ id: chest_id, reward: data.reward, spinning: false });
      
      if (onBalanceChange) {
        onBalanceChange();
      }

      // ✨ Показываем салют! ✨
      setShowFireworks(true);

      // Убираем анимацию и салют через 4 секунды
      animationTimeoutRef.current = setTimeout(() => {
        setAnimationState({ id: null, reward: null, spinning: false });
        setShowFireworks(false);
      }, 4000);

    } catch (e) {
      setMsg(e.message);
      setAnimationState({ id: null, reward: null, spinning: false });
    }
  };

  return (
    <div>
      {/* ✨ Показываем салют, если showFireworks === true ✨ */}
      {showFireworks && <Fireworks />}

      <h2>Сундуки</h2>
      <div className="small" style={{ marginBottom: 12 }}>
        Ваш баланс: {user?.balance ?? 0} монет
      </div>
      <div>
        {chests.map((c) => (
          // ... (JSX для сундуков без изменений) ...
          <div key={c.id} className="poll" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 600 }}>{c.name}</div>
              <div className="small">Цена: {c.price}</div>
            </div>
            <button
              className="btn"
              onClick={() => openChest(c.id)}
              disabled={animationState.spinning}
            >
              {animationState.id === c.id && animationState.spinning ? "Открываем..." : "Открыть"}
            </button>
          </div>
        ))}
      </div>

      {msg && <div style={{ marginTop: 10 }} className="error">{msg}</div>}

      {/* Анимация прокрутки (без изменений) */}
      {animationState.id && (
        <div className="reward-animation">
          <div className="spinner-container">
            {/* ... */}
          </div>
        </div>
      )}
    </div>
  );
}
