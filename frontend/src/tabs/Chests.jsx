// src/tabs/Chests.jsx (С улучшенной логикой анимации)

import React, { useEffect, useState, useRef } from "react";
import Fireworks from "./Fireworks";

export default function Chests({ user, apiRoot, onBalanceChange }) {
  const [chests, setChests] = useState([]);
  const [msg, setMsg] = useState("");
  const [animationState, setAnimationState] = useState({ id: null, reward: null, spinning: false });
  const [showFireworks, setShowFireworks] = useState(false);

  const animationTimeoutRef = useRef(null);

  const fetchChests = async () => {
    // ... тело функции без изменений
    try {
      const res = await fetch(`${apiRoot}/api/chests`);
      if (!res.ok) throw new Error("Ошибка загрузки сундуков");
      const data = await res.json();
      setChests(data || []);
    } catch (e) {
      console.error(e);
      setMsg(e.message);
    }
  };

  useEffect(() => {
    fetchChests();
    return () => {
      if (animationTimeoutRef.current) clearTimeout(animationTimeoutRef.current);
    };
  }, []);

  const openChest = async (chest_id) => {
    setMsg("");
    setShowFireworks(false);
    if (animationTimeoutRef.current) clearTimeout(animationTimeoutRef.current);
    if (!user || !user.telegram_id) {
      setMsg("Ошибка: пользователь не найден");
      return;
    }

    // 1. Запускаем анимацию прокрутки
    setAnimationState({ id: chest_id, reward: null, spinning: true });

    try {
      const res = await fetch(`${apiRoot}/api/chests/open`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ telegram_id: user.telegram_id, chest_id }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Произошла ошибка");
      
      // ✨ ИЗМЕНЕНИЕ: Добавляем задержку перед показом результата
      // Барабан будет крутиться минимум 2 секунды
      setTimeout(() => {
        // 2. Останавливаем барабан на полученной награде
        setAnimationState({ id: chest_id, reward: data.reward, spinning: false });
        
        // 3. Обновляем баланс
        if (onBalanceChange) {
          onBalanceChange();
        }
        
        // 4. Запускаем конфетти
        setShowFireworks(true);

        // 5. Через 4 секунды убираем все эффекты
        animationTimeoutRef.current = setTimeout(() => {
          setAnimationState({ id: null, reward: null, spinning: false });
          setShowFireworks(false);
        }, 4000);
      }, 2000); // 2000ms = 2 секунды

    } catch (e) {
      setMsg(e.message);
      setAnimationState({ id: null, reward: null, spinning: false }); // Сбрасываем анимацию при ошибке
    }
  };

  return (
    <div>
      {showFireworks && <Fireworks />}
      
      <h2>Сундуки</h2>
      <div className="small" style={{ marginBottom: 12 }}>
        Ваш баланс: {user?.balance ?? 0} монет
      </div>
      <div>
        {chests.map((c) => (
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

      {animationState.id && (
        <div className="reward-animation">
          <div className="spinner-container">
            {animationState.spinning && (
              <div className="spinner-reel">
                {[...Array(10)].map((_, i) => <div key={i}>{Math.floor(Math.random() * 900) + 100}</div>)}
              </div>
            )}
            {animationState.reward !== null && (
              <div className="spinner-final-reward">
                {animationState.reward}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
