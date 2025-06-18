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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT trade_time, symbol, side, price, quantity
        FROM trade_history
        ORDER BY id DESC
        LIMIT 50
    """)
    rows = cur.fetchall()
    conn.close()
    return jsonify([
        {"trade_time": r[0], "symbol": r[1], "side": r[2], "price": r[3], "quantity": r[4]}
        for r in rows
    ])

@app.route("/api/news")
def api_news():
    daily = fetch_daily_news()
    return jsonify(daily)

if __name__ == "__main__":
    app.run(debug=True)
