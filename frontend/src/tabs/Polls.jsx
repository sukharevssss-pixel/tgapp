import React, { useEffect, useState } from "react";

export default function Polls({ user, apiRoot }) {
  const [polls, setPolls] = useState([]);
  const [question, setQuestion] = useState("");
  const [optionsText, setOptionsText] = useState(""); // one per line
  const [betAmount, setBetAmount] = useState(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchPolls = async () => {
    try {
      const res = await fetch(`${apiRoot}/api/polls`);
      const data = await res.json();
      setPolls(data || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchPolls();
  }, []);

  const createPoll = async () => {
    setError("");
    const opts = optionsText.split("\n").map(s => s.trim()).filter(Boolean);
    if (!question || opts.length < 2) {
      setError("Нужны вопрос и минимум 2 варианта");
      return;
    }

    if (!user || !user.telegram_id) {
      setError("Ошибка: пользователь не найден");
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
        setError(txt || "Ошибка создания");
      } else {
        setQuestion("");
        setOptionsText("");
        setBetAmount(100);
        fetchPolls();
      }
    } catch (e) {
      setError(String(e));
    }
    setLoading(false);
  };

  const placeBet = async (poll_id, option_id) => {
    setError("");

    if (!user || !user.telegram_id) {
      setError("Ошибка: пользователь не найден");
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
        setError(jd.detail || "Ошибка ставки");
      } else {
        fetchPolls();
      }
    } catch (e) {
      setError(String(e));
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
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button className="btn" onClick={createPoll} disabled={loading}>
          {loading ? "Создается..." : "Создать опрос"}
        </button>
        <div className="small">Ставка с участника: {betAmount} монет</div>
      </div>
      {error && <div className="error">{error}</div>}

      <hr style={{ margin: "12px 0" }} />

      <h2>Активные опросы</h2>
      {polls.length === 0 && <div className="small">Пока нет открытых опросов</div>}
      {polls.map(p => (
        <div key={p.id} className="poll">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div><strong>{p.question}</strong></div>
            <div className="small">Ставка: {p.bet_amount} | Создатель: {p.creator_id}</div>
          </div>
          <div style={{ marginTop: 8 }}>
            {p.options && p.options.map(opt => (
              <div key={opt.id} className="option">
                <div>{opt.option_text}</div>
                <div style={{ display: "flex", gap: 8 }}>
                  <div className="small">Всего: {opt.total_bet}</div>
                  <button className="btn" onClick={() => placeBet(p.id, opt.id)}>
                    Сделать ставку
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

