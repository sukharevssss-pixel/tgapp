// frontend/src/tabs/Polls.jsx (Новая, упрощенная версия)

import React, { useEffect, useState } from "react";

export default function Polls({ user, apiRoot }) {
  const [polls, setPolls] = useState([]);
  // Состояние для хранения сумм ставок пользователя для каждого опроса
  const [betAmounts, setBetAmounts] = useState({});
  const [error, setError] = useState("");

  const fetchPolls = async () => {
    try {
      const res = await fetch(`${apiRoot}/api/polls`);
      const data = await res.json();
      setPolls(data || []);
    } catch (e) {
      console.error(e);
      setError("Не удалось загрузить опросы");
    }
  };

  useEffect(() => {
    fetchPolls();
  }, []);

  // Функция для отслеживания изменения суммы ставки в поле ввода
  const handleBetAmountChange = (pollId, value) => {
    setBetAmounts(prev => ({ ...prev, [pollId]: value }));
  };

  // Функция для размещения ставки
  const placeBet = async (poll_id, option_id) => {
    setError("");
    const poll = polls.find(p => p.id === poll_id);
    if (!poll) return;

    // Берем сумму из состояния или используем минимальную ставку по умолчанию
    const amount = Number(betAmounts[poll_id] || poll.min_bet_amount);

    if (amount < poll.min_bet_amount) {
      setError(`Ставка не может быть меньше ${poll.min_bet_amount}`);
      return;
    }

    try {
      const res = await fetch(`${apiRoot}/api/bet`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          telegram_id: user.telegram_id,
          poll_id,
          option_id,
          amount
        })
      });
      if (!res.ok) {
        const jd = await res.json();
        throw new Error(jd.detail || "Ошибка ставки");
      }
      // Обновляем список опросов, чтобы увидеть новую общую сумму
      fetchPolls();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div>
      <h2>Активные опросы</h2>
      {error && <div className="error">{error}</div>}
      {polls.length === 0 && <div className="small">Открытых опросов пока нет.</div>}
      
      {polls.map(p => {
        const currentBetAmount = betAmounts[p.id] || p.min_bet_amount;
        return (
          <div key={p.id} className="poll">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong>{p.question}</strong>
              <div className="small">Мин. ставка: {p.min_bet_amount}</div>
            </div>
            <div style={{ marginTop: 8 }}>
              {p.options && p.options.map(opt => (
                <div key={opt.id} className="option">
                  <div>{opt.option_text} <span className="small">({opt.total_bet} монет)</span></div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      type="number"
                      className="input"
                      style={{ maxWidth: '80px', textAlign: 'right' }}
                      value={currentBetAmount}
                      onChange={(e) => handleBetAmountChange(p.id, e.target.value)}
                    />
                    <button className="btn" onClick={() => placeBet(p.id, opt.id)}>
                      Поставить
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}