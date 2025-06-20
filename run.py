from flask import Flask, send_from_directory, request, jsonify
import sqlite3
import json

from app.models.database import init_db, DB_PATH
from app.services.price_tracker import get_price
from app.services.binance_sync import sync_trades
from app.services.news_fetcher import fetch_daily_news

app = Flask(
    __name__,
    static_folder="frontend",
    static_url_path=""
)

# 啟動時建立表格並拉取一次交易
init_db()
sync_trades()

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/price")
def api_price():
    symbol = request.args.get("symbol", "cardano")
    price = get_price(symbol)
    return jsonify({"symbol": symbol, "price": price})

@app.route("/api/set-threshold", methods=["POST"])
def api_set_threshold():
    data = request.json
    with open("config.json", "r+") as f:
        cfg = json.load(f)
        cfg.update({
            "symbol": data["symbol"],
            "threshold_low": data["low"],
            "threshold_high": data["high"]
        })
        f.seek(0); f.truncate(); json.dump(cfg, f, indent=2)
    return jsonify({"ok": True})

@app.route("/api/trades")
def api_trades():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 1. 按時間升冪讀出、並合併相同 order_id
    cur.execute("""
      SELECT
        order_id,
        symbol,
        side,
        price,
        SUM(quantity)   AS quantity,
        MIN(trade_time) AS trade_time
      FROM trade_history
      GROUP BY order_id
      ORDER BY datetime(trade_time) ASC
    """)
    records = cur.fetchall()
    conn.close()

    # 2. 計算 profit_pct
    trades = []
    last_buy = {}    # 記錄每個 symbol 最後一次買入價格
    for order_id, symbol, side, price, qty, ttime in records:
        profit_pct = None
        side_u = side.upper()
        if side_u == "BUY":
            last_buy[symbol] = price
        elif side_u == "SELL":
            bp = last_buy.get(symbol)
            if bp and bp > 0:
                profit_pct = round((price - bp) / bp * 100, 2)

        trades.append({
            "trade_time": ttime,
            "symbol":     symbol,
            "side":       side_u,
            "price":      price,
            "quantity":   qty,
            "profit_pct": f"{profit_pct:+.2f}%" if profit_pct is not None else "-"
        })

    # 3. 反轉成最新在前，並只取前 50 筆
    trades = list(reversed(trades))[:50]
    return jsonify(trades)



@app.route("/api/news")
def api_news():
    daily = fetch_daily_news()
    return jsonify(daily)

if __name__ == "__main__":
    app.run(debug=True)
