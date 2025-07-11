// src/pages/PricePage.js

import React, { useState, useEffect, useRef } from "react";
import io from "socket.io-client";

function TradingViewWidget() {
  useEffect(() => {
    if (!window.TradingView) {
      console.error("TradingView script 尚未載入");
      return;
    }
    new window.TradingView.widget({
      container_id: "tradingview-chart",
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
  }, []);

  return <div id="tradingview-chart" style={{ width: "100%", height: 400, marginTop: 16 }} />;
}

export default function PricePage() {
  const [symbol, setSymbol] = useState("");
  const [low, setLow] = useState("");
  const [high, setHigh] = useState("");
  const [latestPrice, setLatestPrice] = useState("--");
  const [socketConnected, setSocketConnected] = useState(false);
  const socketRef = useRef(null);

  // ① 先讀取當前設定
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/config");
        const cfg = await res.json();
        setSymbol(cfg.symbol);
        setLow(cfg.threshold_low);
        setHigh(cfg.threshold_high);
      } catch (err) {
        console.error("fetch config failed:", err);
        setSymbol("cardano");
        setLow(0.5);
        setHigh(0.8);
      }
    })();
  }, []);

  // ② 初始抓一次價格
  useEffect(() => {
    if (!symbol) return;
    (async () => {
      try {
        const res = await fetch(`/api/price?symbol=${symbol}`);
        const data = await res.json();
        if (data.price != null) {
          setLatestPrice(`${symbol.toUpperCase()}: $${data.price.toFixed(4)}`);
        }
      } catch (err) {
        console.error("fetchInitialPrice error:", err);
      }
    })();
  }, [symbol]);

  // ③ Socket.IO 連線 & 監聽
  useEffect(() => {
    // 使用當前域名，避免連到 localhost
    socketRef.current = io(window.location.origin, {
      path: "/socket.io",
      transports: ["websocket"],
      secure: false,
      forceNew: true,  // ✅ 保证每次都新建连接
    });
    const socket = socketRef.current;

    socket.on("connect", () => setSocketConnected(true));
    socket.on("disconnect", () => setSocketConnected(false));
    socket.on("price_update", (data) => {
      if (data.symbol.toLowerCase() === symbol.toLowerCase()) {
        setLatestPrice(`${data.symbol.toUpperCase()}: $${data.price.toFixed(4)}`);
      }
    });

    return () => {
      socket.disconnect();
    };
  }, [symbol]);

  // ④ 更新 threshold 的 handler
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await fetch("/api/set-threshold", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          low: parseFloat(low),
          high: parseFloat(high),
        }),
      });
      alert("設定已更新！");
    } catch (err) {
      console.error("update threshold failed:", err);
    }
  };

  return (
    <section>
      <h3>價格追蹤設定</h3>
      <form className="row g-3" onSubmit={handleSubmit}>
        <div className="col-md-4">
          <label className="form-label">幣種</label>
          <input
            className="form-control"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            required
          />
        </div>
        <div className="col-md-4">
          <label className="form-label">價格下限</label>
          <input
            type="number"
            step="0.01"
            className="form-control"
            value={low}
            onChange={(e) => setLow(e.target.value)}
            required
          />
        </div>
        <div className="col-md-4">
          <label className="form-label">價格上限</label>
          <input
            type="number"
            step="0.01"
            className="form-control"
            value={high}
            onChange={(e) => setHigh(e.target.value)}
            required
          />
        </div>
        <div className="col-12">
          <button type="submit" className="btn btn-primary">
            更新設定
          </button>
        </div>
      </form>

      <hr />

      <h5>
        即時價格{' '}
        <span
          style={{
            display: "inline-block",
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: socketConnected ? "green" : "red",
            marginLeft: 8,
          }}
          title={socketConnected ? "Socket 已連線" : "Socket 未連線"}
        />
      </h5>
      <p style={{ fontSize: "1.5rem" }}>{latestPrice}</p>

      <TradingViewWidget />
    </section>
  );
}
