import React, { useEffect, useState } from "react";
import Polls from "./tabs/Polls";
import Chests from "./tabs/Chests";
import Rating from "./tabs/Rating";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function TabButton({ children, active, onClick }) {
  return (
    <button className={`tab-button ${active ? "active" : ""}`} onClick={onClick}>
      {children}
    </button>
  );
}

export default function App() {
  const [tab, setTab] = useState("polls");
  const [user, setUser] = useState(null);
  const [loadingUser, setLoadingUser] = useState(true);

  useEffect(() => {
    const initLocal = async (uid, username) => {
      try {
        const res = await fetch(`${API}/api/init`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: uid, username }),
        });
        const data = await res.json();
        setUser(data); // API возвращает объект { user_id, username, balance }
      } catch (e) {
        console.error("api init error", e);
      } finally {
        setLoadingUser(false);
      }
    };

    if (window.Telegram && window.Telegram.WebApp) {
      try {
        const initDataUnsafe = window.Telegram.WebApp.initDataUnsafe || {};
        if (initDataUnsafe.user) {
          const u = initDataUnsafe.user;
          initLocal(u.id, u.username || `${u.first_name || "user"}`);
          return;
        }
      } catch (e) {
        console.warn("Telegram WebApp init error", e);
      }
    }

    // fallback для локального запуска
    initLocal(1, "testuser");
  }, []);

  if (loadingUser) return <div className="container">Загрузка пользователя...</div>;
  if (!user) return <div className="container">Ошибка: пользователь не найден</div>;

  return (
    <div className="container">
      <h1>TG MiniApp — Demo</h1>

      {/* ⚡️ Блок профиля */}
      <div className="profile-box">
        👤 <b>{user.username}</b> | 🆔 {user.user_id} | 💰 {user.balance} монет
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
        {tab === "polls" && <Polls user={user} apiRoot={API} />}
        {tab === "chests" && <Chests user={user} apiRoot={API} />}
        {tab === "rating" && <Rating apiRoot={API} />}
      </div>
    </div>
  );
}
