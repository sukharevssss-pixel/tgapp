import React, { useEffect, useState } from "react";
import Polls from "./tabs/Polls";
import Chests from "./tabs/Chests";
import Rating from "./tabs/Rating";
import "./App.css";

// URL вашего бэкенда
const API_URL = "https://tgapp-4ugf.onrender.com"; 

function TabButton({ children, active, onClick }) {
  return (
    <button
      className={`tab-button ${active ? "active" : ""}`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export default function App() {
  const [tab, setTab] = useState("polls");
  const [user, setUser] = useState(null);
  const [loadingUser, setLoadingUser] = useState(true);

  useEffect(() => {
    const initUser = async (telegram_id, username) => {
      try {
        const res = await fetch(`${API_URL}/api/auth`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ telegram_id, username }),
        });
        const data = await res.json();
        if (data?.ok && data.user) {
          setUser(data.user);
        } else {
          console.warn("⚠️ Сервер вернул ошибку:", data);
        }
      } catch (e) {
        console.error("🔥 Ошибка запроса api/auth:", e);
      } finally {
        setLoadingUser(false);
      }
    };

    const tg = window.Telegram?.WebApp;
    if (tg && tg.initDataUnsafe?.user) {
      const u = tg.initDataUnsafe.user;
      initUser(u.id, u.username || u.first_name || "user");
    } else {
      // Fallback для локального запуска
      initUser(1, "testuser");
    }
  }, []);

  /**
   * Функция для обновления данных пользователя с сервера.
   * Она будет передана в дочерние компоненты, которые могут менять баланс.
   */
  const refreshUser = async () => {
    if (!user) return;
    try {
      const res = await fetch(`${API_URL}/api/me/${user.telegram_id}`);
      if (res.ok) {
        const updatedUserData = await res.json();
        // Обновляем состояние, сохраняя предыдущие данные на случай,
        // если API вернет неполный объект
        setUser(prevUser => ({ ...prevUser, ...updatedUserData }));
      }
    } catch (e) {
      console.error("🔥 Ошибка обновления пользователя:", e);
    }
  };

  if (loadingUser) {
    return <div className="container">⏳ Загрузка пользователя...</div>;
  }

  if (!user) {
    return <div className="container">❌ Ошибка: пользователь не найден</div>;
  }

  return (
    <div className="container">
      <h1>TG MiniApp — Demo</h1>
      <div className="profile-box">
        👤 <b>{user.username}</b> | 🆔 {user.telegram_id} | 💰 {user.balance} монет
      </div>

      <div className="tab-buttons">
        <TabButton active={tab === "polls"} onClick={() => setTab("polls")}>
          📊 Опросы
        </TabButton>
        <TabButton active={tab === "chests"} onClick={() => setTab("chests")}>
          🎁 Сундуки
        </TabButton>
        <TabButton active={tab === "rating"} onClick={() => setTab("rating")}>
          🏆 Рейтинг
        </TabButton>
      </div>

      <div className="content">
        {tab === "polls" && <Polls user={user} apiRoot={API_URL} />}
        {tab === "chests" && (
          <Chests 
            user={user} 
            apiRoot={API_URL} 
            onBalanceChange={refreshUser} // Передаем функцию как пропс
          />
        )}
        {tab === "rating" && <Rating apiRoot={API_URL} />}
      </div>
    </div>
  );
}
