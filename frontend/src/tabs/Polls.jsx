import React, { useEffect, useState } from "react";

export default function Polls({ user, apiRoot }) {
  // ... (весь код до return остаётся без изменений) ...
  const [polls, setPolls] = useState([]);
  const [question, setQuestion] = useState("");
  const [optionsText, setOptionsText] = useState("");
  const [betAmount, setBetAmount] = useState(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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

  useEffect(() => {
    fetchPolls();
  }, []);

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
      
      fetchPolls();

    } catch (e) {
      setError(e.message);
    }
  };

  const closePoll = async (poll_id, winning_option_id) => {
    setError("");
    if (!user || !user.telegram_id) {
      setError("Ошибка: пользователь не найден.");
      return;
    }

    if (!window.confirm("Вы уверены, что хотите закрыть опрос с этим победителем? Это действие нельзя отменить.")) {
      return;
    }

    try {
      const res = await fetch(`${apiRoot}/api/polls/close`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          telegram_id: user.telegram_id,
          poll_id,
          winning_option_id
        })
      });

      if (!res.ok) {
        const jd = await res.json();
        throw new Error(jd.detail || "Ошибка при закрытии опроса");
      }
      
      fetchPolls();

    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div>
      {/* ... (форма создания опроса без изменений) ... */}
      <h2>Создать опрос</h2>
      <div className="form-row">
        <input className="input" placeholder="Вопрос" value={question} onChange={e => setQuestion(e.target.value)} />
        <input type="number" className="input" style={{ maxWidth: 120 }} value={betAmount} onChange={e => setBetAmount(e.target.value)} />
      </div>
      <div className="form-row">
        <textarea className="input" rows={3} placeholder="Каждый вариант с новой строки" value={optionsText} onChange={e => setOptionsText(e.target.value)} />
      </div>
      <div style={{ display: "flex", gap: 8, marginBottom: 12, alignItems: "center" }}>
        <button className="btn" onClick={createPoll} disabled={loading}>{loading ? "Создание..." : "Создать опрос"}</button>
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
                  
                  {/* --- ✨ НАЧАЛО ИЗМЕНЕНИЙ ✨ --- */}

                  {/* Кнопка для ставки теперь видна всем, включая создателя */}
                  <button className="btn" onClick={() => placeBet(p.id, opt.id)}>
                    Сделать ставку
                  </button>
                  
                  {/* Кнопка администратора добавляется, только если пользователь — создатель */}
                  {user && user.telegram_id === p.creator_id && (
                    <button className="btn-admin" title="Выбрать как победителя и закрыть опрос" onClick={() => closePoll(p.id, opt.id)}>
                      👑 Победитель
                    </button>
                  )}

                  {/* --- ✨ КОНЕЦ ИЗМЕНЕНИЙ ✨ --- */}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
