import React, { useState, useEffect, useRef } from "react";

function TradingViewWidget() {
  const chartRef = useRef(null);
  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/tv.js";
    script.async = true;
    script.onload = () => {
      if (window.TradingView) {
        new window.TradingView.widget({
          container_id: "chart",
          autosize: true,
          symbol: "BINANCE:ADAUSDT",
          interval: "240",
          timezone: "Asia/Taipei",
          theme: "light",
          style: "1",
          locale: "zh_TW",
          toolbar_bg: "#f1f3f6",
          enable_publishing: false,
          allow_symbol_change: false,
          hide_side_toolbar: false,
          details: true,
          hotlist: true,
        });
      }
    };
    document.body.appendChild(script);
    return () => {
      document.body.removeChild(script);
    };
  }, []);
  return <div id="chart" ref={chartRef} style={{ height: 400, marginTop: 16 }} />;
}

export default function PricePage() {
  const [symbol, setSymbol] = useState("cardano");
  const [low, setLow] = useState(0.5);
  const [high, setHigh] = useState(0.8);
  const [latestPrice, setLatestPrice] = useState("--");

  const fetchLatestPrice = async () => {
    const res = await fetch(`/api/price?symbol=${symbol}`);
    const data = await res.json();
    setLatestPrice(`${symbol.toUpperCase()}: $${data.price}`);
  };

  useEffect(() => {
    fetchLatestPrice();
    const timer = setInterval(fetchLatestPrice, 600000);
    return () => clearInterval(timer);
    // eslint-disable-next-line
  }, [symbol]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = { symbol, low: parseFloat(low), high: parseFloat(high) };
    await fetch("/api/set-threshold", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    alert("設定已更新！");
  };

  return (
    <section>
      <h3>價格追蹤設定</h3>
      <form className="row g-3" onSubmit={handleSubmit}>
        <div className="col-md-4">
          <label className="form-label">幣種</label>
          <input className="form-control" value={symbol} onChange={e => setSymbol(e.target.value)} />
        </div>
        <div className="col-md-4">
          <label className="form-label">價格下限</label>
          <input type="number" step="0.01" className="form-control" value={low} onChange={e => setLow(e.target.value)} />
        </div>
        <div className="col-md-4">
          <label className="form-label">價格上限</label>
          <input type="number" step="0.01" className="form-control" value={high} onChange={e => setHigh(e.target.value)} />
        </div>
        <div className="col-12">
          <button type="submit" className="btn btn-primary">更新設定</button>
        </div>
      </form>
      <hr />
      <h5>最新價格</h5>
      <p>{latestPrice}</p>
      <TradingViewWidget />
    </section>
  );
}
