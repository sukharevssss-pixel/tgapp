import React, { useEffect, useState, useRef } from "react";

export default function Chests({ user, apiRoot, onBalanceChange }) {
  const [chests, setChests] = useState([]);
  const [msg, setMsg] = useState("");
  
  // Состояние для управления анимацией
  const [animationState, setAnimationState] = useState({ id: null, reward: null, spinning: false });

  // Ссылка на таймер для сброса анимации
  const animationTimeoutRef = useRef(null);

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
    // Очищаем таймер при размонтировании компонента
    return () => {
      if (animationTimeoutRef.current) {
        clearTimeout(animationTimeoutRef.current);
      }
    };
  }, []);

  const openChest = async (chest_id) => {
    // Очищаем предыдущее сообщение и таймер
    setMsg("");
    if (animationTimeoutRef.current) {
      clearTimeout(animationTimeoutRef.current);
    }

    if (!user || !user.telegram_id) {
      setMsg("Ошибка: пользователь не найден");
      return;
    }

    // Запускаем анимацию для конкретного сундука
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
      
      // Останавливаем анимацию на финальной награде
      setAnimationState({ id: chest_id, reward: data.reward, spinning: false });
      
      // Вызываем обновление баланса в родительском компоненте
      if (onBalanceChange) {
        onBalanceChange();
      }

      // Убираем блок с анимацией через 3 секунды
      animationTimeoutRef.current = setTimeout(() => {
        setAnimationState({ id: null, reward: null, spinning: false });
      }, 3000);

    } catch (e) {
      setMsg(e.message);
      // Сбрасываем анимацию при ошибке
      setAnimationState({ id: null, reward: null, spinning: false });
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
          <div key={c.id} className="poll" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 600 }}>{c.name}</div>
              <div className="small">Цена: {c.price}</div>
            </div>
            <button
              className="btn"
              onClick={() => openChest(c.id)}
              disabled={animationState.spinning} // Блокируем все кнопки во время любой анимации
            >
              {animationState.id === c.id && animationState.spinning ? "Открываем..." : "Открыть"}
            </button>
          </div>
        ))}
      </div>

      {/* Блок для вывода сообщения об ошибке */}
      {msg && <div style={{ marginTop: 10 }} className="error">{msg}</div>}

      {/* Новый блок для анимации и результата */}
      {animationState.id && (
        <div className="reward-animation">
          <div className="small" style={{ marginBottom: '5px' }}>Ваш выигрыш:</div>
          <div className="spinner-container">
            {animationState.spinning && (
              <div className="spinner-reel">
                {/* Генерируем случайные числа для эффекта прокрутки */}
                {[...Array(10)].map((_, i) => <div key={i}>{Math.floor(Math.random() * 800) + 100}</div>)}
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
