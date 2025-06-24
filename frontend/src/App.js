import React from "react";
import { BrowserRouter, Routes, Route, Link, NavLink } from "react-router-dom";
import PricePage from "./pages/PricePage";
import TradesPage from "./pages/TradesPage";
import NewsPage from "./pages/NewsPage";
import ToolsPage from "./pages/ToolsPage";

export default function App() {
  return (
    <BrowserRouter>
      <nav className="navbar navbar-expand-lg navbar-light bg-light">
        <div className="container-fluid">
          <Link className="navbar-brand" to="/">Crypto Dashboard</Link>
          <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav"
            aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
            <span className="navbar-toggler-icon"></span>
          </button>
          <div className="collapse navbar-collapse" id="navbarNav">
            <ul className="navbar-nav">
              <li className="nav-item"><NavLink className="nav-link" to="/">價格設定</NavLink></li>
              <li className="nav-item"><NavLink className="nav-link" to="/trades">交易紀錄</NavLink></li>
              <li className="nav-item"><NavLink className="nav-link" to="/news">新聞摘要</NavLink></li>
              <li className="nav-item"><NavLink className="nav-link" to="/tools">筆記管理</NavLink></li>
            </ul>
          </div>
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
  );
}
