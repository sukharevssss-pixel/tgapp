import React, { useState, useEffect } from "react";
import Polls from "./tabs/Polls";
import Chests from "./tabs/Chests";
import Rating from "./tabs/Rating";
import "./App.css"; // свои стили

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`tab-button ${active ? "active" : ""}`}
    >
      {children}
    </button>
  );
}

export default function App() {
  const [tab, setTab] = useState("polls");
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (window.Telegram && window.Telegram.WebApp) {
      try {
        const initDataUnsafe = window.Telegram.WebApp.initDataUnsafe || {};
        if (initDataUnsafe.user) {
          const u = initDataUnsafe.user;
          const newUser = { user_id: u.id, username: u.username };
          setUser(newUser);
          fetch((import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api/init", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(newUser),
          });
        }
      } catch (e) {
        console.warn("Telegram WebApp init error", e);
      }
    } else {
      // 🔹 Фолбэк для локальной разработки
      const testUser = { user_id: 1, username: "testuser" };
      setUser(testUser);
      fetch((import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api/init", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(testUser),
      });
    }
  }, []);

  return (
    <div className="container">
      <h1>TG MiniApp — Demo</h1>

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
        {tab === "polls" && <Polls user={user} />}
        {tab === "chests" && <Chests user={user} />}
        {tab === "rating" && <Rating user={user} />}
      </div>
    </div>
  );
}