import React, { useEffect, useState } from "react";
import Polls from "./tabs/Polls";
import Chests from "./tabs/Chests";
import Rating from "./tabs/Rating";
import "./App.css";
import DebugUser from "./DebugUser";

const API_URL = "https://tgapp-4ugf.onrender.com"; // ваш backend

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
  // Добавим состояние для отладочной информации
  const [debugInfo, setDebugInfo] = useState(null);

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
          setDebugInfo({ error: "Сервер вернул ошибку", details: data });
        }
      } catch (e) {
        console.error("🔥 Ошибка запроса api/auth:", e);
        setDebugInfo({ error: "Ошибка запроса api/auth", details: e.message });
      } finally {
        setLoadingUser(false);
      }
    };

    // --- НАЧАЛО ИЗМЕНЕНИЙ ---

    // Попытка получить данные из Telegram WebApp
    const tg = window.Telegram?.WebApp;

    // Выводим в консоль, чтобы видеть, что происходит
    console.log("window.Telegram.WebApp:", tg);

    if (tg && tg.initDataUnsafe?.user) {
      // ✅ Мы внутри Telegram, используем реальные данные
      console.log("Приложение запущено в Telegram.");
      const u = tg.initDataUnsafe.user;
      setDebugInfo({ message: "Данные из Telegram WebApp", user: u });
      initUser(u.id, u.username || u.first_name || "user");
    } else {
      // ❌ Мы в обычном браузере, используем тестовые данные
      console.log("Приложение запущено в браузере (режим разработки).");
      setDebugInfo({ error: "❌ Telegram.WebApp не найден. Используется тестовый пользователь." });
      // fallback для локального запуска (НЕ для продакшена!)
      initUser(1, "testuser");
    }

    // --- КОНЕЦ ИЗМЕНЕНИЙ ---
  }, []);

  if (loadingUser) {
    return <div className="container">⏳ Загрузка пользователя...</div>;
  }

  if (!user) {
    // Показываем отладочную информацию, если есть ошибка
    return (
      <div className="container">
        ❌ Ошибка: пользователь не найден
        {debugInfo?.error && <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>{JSON.stringify(debugInfo, null, 2)}</pre>}
      </div>
    );
  }

  return (
    <div className="container">
      <h1>TG MiniApp — Demo</h1>

      {/* 🔍 Отображаем блок с отладочной информацией */}
      {debugInfo && (
        <div style={{ background: "#333", padding: '10px', borderRadius: '8px', margin: '10px 0' }}>
          <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-all", color: 'white' }}>
            {JSON.stringify(debugInfo, null, 2)}
          </pre>
        </div>
      )}
      
      {/* Ваш DebugUser компонент тоже можно использовать */}
      {/* <DebugUser /> */}

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
