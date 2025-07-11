import React, { createContext, useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Link, NavLink } from "react-router-dom";
import PricePage from "./pages/PricePage";
import TradesPage from "./pages/TradesPage";
import NewsPage from "./pages/NewsPage";
import ToolsPage from "./pages/ToolsPage";
import { io } from "socket.io-client";

// 建立 Socket.IO 的 Context，供子組件取得相同實例
export const SocketContext = createContext(null);

export default function App() {
  const [socket, setSocket] = useState(null);
  const [price, setPrice] = useState(null);

  useEffect(() => {
    const sock = io(window.location.origin, {
      path: "/socket.io",
      transports: ["websocket"],
    });
    sock.on("price_update", (data) => {
      console.log("收到實時價格：", data);
      if (data?.price != null) setPrice(data.price.toFixed(6));
    });
    sock.on("connect_error", (err) => {
      console.error("Socket.IO 連線失敗，重試中…", err);
    });
    setSocket(sock);
    return () => sock.disconnect();
  }, []);

  return (
    <SocketContext.Provider value={socket}>
      <BrowserRouter>
        {/* Navbar：去掉 collapse，改为 flex 布局，左对齐，垂直居中 */}
        <nav className="navbar navbar-light bg-light">
          <div className="d-flex w-100 align-items-center">
            <Link className="navbar-brand me-4" to="/">
              Crypto Dashboard
            </Link>
            <ul className="navbar-nav flex-row">
              <li className="nav-item me-3">
                <NavLink className="nav-link" to="/">
                  價格設定
                  {price != null && (
                    <span className="badge bg-secondary ms-1">
                      {price} USD
                    </span>
                  )}
                </NavLink>
              </li>
              <li className="nav-item me-3">
                <NavLink className="nav-link" to="/trades">
                  交易紀錄
                </NavLink>
              </li>
              <li className="nav-item me-3">
                <NavLink className="nav-link" to="/news">
                  新聞摘要
                </NavLink>
              </li>
              <li className="nav-item">
                <NavLink className="nav-link" to="/tools">
                  筆記管理
                </NavLink>
              </li>
            </ul>
          </div>
        </nav>

        <div className="container mt-4">
          <Routes>
            <Route path="/" element={<PricePage />} />
            <Route path="/trades" element={<TradesPage />} />
            <Route path="/news" element={<NewsPage />} />
            <Route path="/tools" element={<ToolsPage />} />
          </Routes>
        </div>
      </BrowserRouter>
    </SocketContext.Provider>
  );
}
