import React, { useEffect, useState } from "react";
import Polls from "./tabs/Polls";
import Chests from "./tabs/Chests";
import Rating from "./tabs/Rating";
import "./App.css";
import DebugUser from "./DebugUser";

const API_URL = "https://tgapp-4ugf.onrender.com"; // твой backend

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
  console.log("window.Telegram:", window.Telegram);
  console.log("window.Telegram?.WebApp:", window.Telegram?.WebApp);

  if (window.Telegram && window.Telegram.WebApp) {
    try {
      const initDataUnsafe = window.Telegram.WebApp.initDataUnsafe || {};
      console.log("initDataUnsafe:", initDataUnsafe);
      if (initDataUnsafe.user) {
        const u = initDataUnsafe.user;
        initUser(u.id, u.username || `${u.first_name || "user"}`);
        return;
      }
    } catch (e) {
      console.warn("Telegram WebApp init error", e);

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

    // ⚡️ получаем юзера из Telegram WebApp
    try {
      const tg = window.Telegram?.WebApp;
      const u = tg?.initDataUnsafe?.user;
      if (u) {
        initUser(u.id, u.username || u.first_name || "user");
        return;
      }
    } catch (e) {
      console.warn("⚠️ Telegram WebApp init error:", e);
    }

    // fallback для локального запуска (НЕ для продакшена!)
    initUser(1, "testuser");
  }, []);

  if (loadingUser) {
    return <div className="container">⏳ Загрузка пользователя...</div>;
  }

  if (!user) {
    return <div className="container">❌ Ошибка: пользователь не найден</div>;
  }

  return (
    <div className="container">
      <h1>TG MiniApp — Demo</h1>

    {/* 🔍 Debug блок для проверки initData */}
    <DebugUser />

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
        {tab === "chests" && <Chests user={user} apiRoot={API_URL} />}
        {tab === "rating" && <Rating apiRoot={API_URL} />}
      </div>
    </div>
  );
}

