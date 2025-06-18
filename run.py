from flask import Flask, send_from_directory, request, jsonify
from app.models.database import init_db, save_price, save_trade
from app.services.price_tracker import get_current_price
from app.services.binance_sync import sync_trades
from app.services.news_fetcher import fetch_daily_news

app = Flask(
    __name__,
    static_folder="frontend",      # 靜態檔案目錄
    static_url_path=""             # 讓 "/" 指向 index.html
)

# 啟動時確保資料庫與表存在
init_db()

@app.route("/")
def index():
    # 直接回傳 frontend/index.html
    return send_from_directory(app.static_folder, "index.html")

# API：取得即時價格
@app.route("/api/price")
def api_price():
    symbol = request.args.get("symbol", "cardano")
    price = get_current_price(symbol)
    return jsonify({"symbol": symbol, "price": price})

# API：更新門檻（寫入 config.json 或資料庫）
@app.route("/api/set-threshold", methods=["POST"])
def api_set_threshold():
    data = request.json
    # 這裡你可以把設定寫回 config.json 或資料庫
    # 假設我們寫回 config.json：
    import json
    with open("config.json","r+") as f:
        cfg = json.load(f)
        cfg.update({
            "symbol": data["symbol"],
            "threshold_low": data["low"],
            "threshold_high": data["high"]
        })
        f.seek(0); f.truncate(); json.dump(cfg, f, indent=2)
    return jsonify({"ok": True})

# API：回傳交易紀錄
@app.route("/api/trades")
def api_trades():
    # （假設你已經用 sync_trades() 同步過資料庫）
    import sqlite3
    conn = sqlite3.connect("app/models/price_history.db")
    cur = conn.cursor()
    cur.execute("SELECT trade_time, symbol, side, price, quantity FROM trade_history ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall()
    conn.close()
    return jsonify([
        {"trade_time": r[0], "symbol": r[1], "side": r[2], "price": r[3], "quantity": r[4]}
        for r in rows
    ])

# API：回傳當日新聞
@app.route("/api/news")
def api_news():
    news = fetch_daily_news()
    return jsonify(news)

if __name__ == "__main__":
    # Flask 伺服器啟動後，打開瀏覽器到 http://127.0.0.1:5000/
    app.run(debug=True)
