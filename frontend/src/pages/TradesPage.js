import React, { useEffect, useState } from "react";

export default function TradesPage() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTrades() {
      setLoading(true);
      try {
        const res = await fetch("/api/trades");
        const data = await res.json();
        setTrades(data);
      } catch (err) {
        setTrades([]);
      }
      setLoading(false);
    }
    fetchTrades();
  }, []);

  return (
    <section>
      <h3>幣安交易紀錄</h3>
      {loading ? (
        <div>載入中...</div>
      ) : (
        <table className="table table-striped" id="tradesTable">
          <thead>
            <tr>
              <th>時間</th>
              <th>幣種</th>
              <th>買/賣</th>
              <th>價格</th>
              <th>獲利%</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t, i) => (
              <tr key={i}>
                <td>{t.trade_time}</td>
                <td>{t.symbol}</td>
                <td>{t.side}</td>
                <td>{t.price}</td>
                <td>{t.profit_pct}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
