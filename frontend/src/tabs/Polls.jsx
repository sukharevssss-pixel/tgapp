import React, { useEffect, useState } from "react";

export default function Polls({ user, apiRoot }) {
  const [polls, setPolls] = useState([]);
  const [question, setQuestion] = useState("");
  const [optionsText, setOptionsText] = useState("");
  
  // ✨ Переименовываем состояние для ясности
  const [minBetAmount, setMinBetAmount] = useState(100);
  
  // ✨ Новое состояние для хранения сумм ставок пользователя для каждого опроса
  const [betAmounts, setBetAmounts] = useState({});

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchPolls = async () => { /* ... без изменений ... */ };
  useEffect(() => { fetchPolls(); }, []);

  const handleBetAmountChange = (pollId, value) => {
    setBetAmounts(prev => ({
      ...prev,
      [pollId]: Number(value)
    }));
  };

  const createPoll = async () => {
    // ...
    // ✨ Используем новое имя переменной
    const res = await fetch(`${apiRoot}/api/polls`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            telegram_id: user.telegram_id,
            question,
            options: opts,
            min_bet_amount: Number(minBetAmount) // Отправляем min_bet_amount
        })
    });
    // ...
  };

  // ✨ Функция теперь принимает amount
  const placeBet = async (poll_id, option_id, amount) => {
    setError("");
    const poll = polls.find(p => p.id === poll_id);
    if (!poll) return;

    if (amount < poll.min_bet_amount) {
      setError(`Ставка не может быть меньше ${poll.min_bet_amount}`);
      return;
    }
    // ...
    const res = await fetch(`${apiRoot}/api/bet`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            telegram_id: user.telegram_id,
            poll_id,
            option_id,
            amount // Отправляем сумму ставки
        })
    });
    // ...
  };

  const closePoll = async (poll_id, winning_option_id) => { /* ... без изменений ... */ };

  return (
    <div>
      <h2>Создать опрос</h2>
      <div className="form-row">
        <input className="input" placeholder="Вопрос" value={question} onChange={e => setQuestion(e.target.value)} />
        {/* ✨ Изменяем поле для ввода минимальной ставки */}
        <input
          type="number"
          className="input"
          style={{ maxWidth: 140 }}
          value={minBetAmount}
          onChange={e => setMinBetAmount(e.target.value)}
        />
      </div>
      {/* ... остальная форма без изменений ... */}
      <div className="small">Минимальная ставка: {minBetAmount} монет</div>

      <hr style={{ margin: "20px 0" }} />

      <h2>Активные опросы</h2>
      {polls.map(p => {
        // Определяем текущую сумму ставки для этого опроса
        const currentBetAmount = betAmounts[p.id] || p.min_bet_amount;
        return (
          <div key={p.id} className="poll">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div><strong>{p.question}</strong></div>
              {/* ✨ Отображаем минимальную ставку */}
              <div className="small">Мин. ставка: {p.min_bet_amount}</div>
            </div>
            <div style={{ marginTop: 8 }}>
              {p.options && p.options.map(opt => (
                <div key={opt.id} className="option">
                  <div>{opt.option_text} <span className="small">({opt.total_bet} монет)</span></div>
                  {/* ✨ ИЗМЕНЕНИЕ: Теперь здесь форма для ставки, а не просто кнопка */}
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      type="number"
                      className="input"
                      style={{ maxWidth: '80px', textAlign: 'right' }}
                      value={currentBetAmount}
                      onChange={(e) => handleBetAmountChange(p.id, e.target.value)}
                      placeholder={`>${p.min_bet_amount}`}
                    />
                    <button className="btn" onClick={() => placeBet(p.id, opt.id, currentBetAmount)}>
                      Поставить
                    </button>
                    {user && user.telegram_id === p.creator_id && (
                      <button className="btn-admin" onClick={() => closePoll(p.id, opt.id)}>👑</button>
                    )}
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