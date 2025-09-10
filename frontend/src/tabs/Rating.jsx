import React, { useEffect, useState } from "react";

export default function Rating({ apiRoot }) {
  const [list, setList] = useState([]);

  const fetchRating = async () => {
    try {
      const res = await fetch(`${apiRoot}/api/rating`);
      const data = await res.json();
      setList(data || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => { fetchRating(); }, []);

  return (
    <div>
      <h2>Рейтинг игроков</h2>
      <table className="table">
        <thead>
          <tr><th>#</th><th>Ник</th><th>Баланс</th><th>Wins</th><th>Losses</th><th>Winrate</th></tr>
        </thead>
        <tbody>
          {list.map((u,i) => (
            <tr key={u.user_id}>
              <td>{i+1}</td>
              <td>{u.username || u.user_id}</td>
              <td>{u.balance}</td>
              <td>{u.wins}</td>
              <td>{u.losses}</td>
              <td>{(u.winrate*100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
