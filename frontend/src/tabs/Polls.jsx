import React, { useEffect, useState } from "react";

export default function Polls({ user, apiRoot }) {
  const [polls, setPolls] = useState([]);
  const [question, setQuestion] = useState("");
  const [optionsText, setOptionsText] = useState(""); // Варианты, каждый с новой строки
  const [betAmount, setBetAmount] = useState(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Функция для загрузки активных опросов с сервера
  const fetchPolls = async () => {
    try {
      const res = await fetch(`${apiRoot}/api/polls`);
      if (!res.ok) throw new Error("Ошибка при загрузке опросов");
      const data = await res.json();
      setPolls(data || []);
    } catch (e) {
      console.error(e);
      setError("Не удалось загрузить опросы.");
    }
  };

  // Загружаем опросы при первом рендере компонента
  useEffect(() => {
    fetchPolls();
  }, []);

  // Функция для создания нового опроса
  const createPoll = async () => {
    setError("");
    const opts = optionsText.split("\n").map(s => s.trim()).filter(Boolean);

    if (!question || opts.length < 2) {
      setError("Необходимо указать вопрос и как минимум 2 варианта ответа.");
      return;
    }
    if (!user || !user.telegram_id) {
      setError("Ошибка: пользователь не найден. Перезагрузите приложение.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${apiRoot}/api/polls`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          telegram_id: user.telegram_id,
          question,
          options: opts,
          bet_amount: Number(betAmount)
        })
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Ошибка при создании опроса");
      }

      // Сбрасываем поля и обновляем список опросов
      setQuestion("");
      setOptionsText("");
      setBetAmount(100);
      fetchPolls();

    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Функция для размещения ставки
  const placeBet = async (poll_id, option_id) => {
    setError("");
    if (!user || !user.telegram_id) {
      setError("Ошибка: пользователь не найден.");
      return;
    }

    try {
      const res = await fetch(`${apiRoot}/api/bet`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          telegram_id: user.telegram_id,
          poll_id,
          option_id
        })
      });

      if (!res.ok) {
        const jd = await res.json();
        throw new Error(jd.detail || "Ошибка ставки");
      }
      
      // Обновляем данные опросов, чтобы увидеть изменения
      fetchPolls();

    } catch (e) {
      setError(e.message);
    }
  };

  // Функция для закрытия опроса (только для создателя)
  const closePoll = async (poll_id, winning_option_id) => {
    setError("");
    if (!user || !user.telegram_id) {
      setError("Ошибка: пользователь не найден.");
      return;
    }

    // Запрашиваем подтверждение перед закрытием
    if (!window.confirm("Вы уверены, что хотите закрыть опрос с этим победителем? Это действие нельзя отменить.")) {
      return;
    }

    try {
      const res = await fetch(`${apiRoot}/api/polls/close`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          telegram_id: user.telegram_id, // Отправляем ID для проверки прав на бэкенде
          poll_id,
          winning_option_id
        })
      });

      if (!res.ok) {
        const jd = await res.json();
        throw new Error(jd.detail || "Ошибка при закрытии опроса");
      }
      
      // Обновляем список, чтобы закрытый опрос исчез
      fetchPolls();

    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div>
      <h2>Создать опрос</h2>
      <div className="form-row">
        <input
          className="input"
          placeholder="Вопрос"
          value={question}
          onChange={e => setQuestion(e.target.value)}
        />
        <input
          type="number"
          className="input"
          style={{ maxWidth: 120 }}
          value={betAmount}
          onChange={e => setBetAmount(e.target.value)}
        />
      </div>
      <div className="form-row">
        <textarea
          className="input"
          rows={3}
          placeholder="Каждый вариант с новой строки"
          value={optionsText}
          onChange={e => setOptionsText(e.target.value)}
        />
      </div>
      <div style={{ display: "flex", gap: 8, marginBottom: 12, alignItems: "center" }}>
        <button className="btn" onClick={createPoll} disabled={loading}>
          {loading ? "Создание..." : "Создать опрос"}
        </button>
        <div className="small">Ставка с участника: {betAmount} монет</div>
      </div>
      {error && <div className="error">{error}</div>}

      <hr style={{ margin: "20px 0" }} />

      <h2>Активные опросы</h2>
      {polls.length === 0 && <div className="small">Пока нет открытых опросов. Создайте первый!</div>}
      
      {polls.map(p => (
        <div key={p.id} className="poll">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div><strong>{p.question}</strong></div>
            <div className="small">Ставка: {p.bet_amount} | ID создателя: {p.creator_id}</div>
          </div>
          <div style={{ marginTop: 8 }}>
            {p.options && p.options.map(opt => (
              <div key={opt.id} className="option">
                <div>{opt.option_text}</div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <div className="small">Всего поставлено: {opt.total_bet}</div>
                  
                  {/* Логика отображения кнопок */}
                  {user && user.telegram_id === p.creator_id ? (
                    // Если текущий пользователь — создатель, показать кнопку для выбора победителя
                    <button className="btn-admin" title="Выбрать как победителя и закрыть опрос" onClick={() => closePoll(p.id, opt.id)}>
                      👑 Победитель
                    </button>
                  ) : (
                    // Иначе показать кнопку для ставки
                    <button className="btn" onClick={() => placeBet(p.id, opt.id)}>
                      Сделать ставку
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
